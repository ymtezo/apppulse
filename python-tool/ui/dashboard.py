import logging
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox

# Add parent to path for imports
sys.path.insert(0, __file__.rsplit("\\", 2)[0])

from config import DEVICE_ID, APP_NAME
from storage.database import (
    init_db, get_deletion_log, insert_rejection, get_rejection_count,
)
from tracker.usage_aggregator import (
    get_top_apps, get_bottom_apps, format_duration,
)
from manager.app_inventory import scan_installed_apps, get_all_apps
from manager.uninstaller import uninstall, is_blocked
from recommender.alternatives import get_alternatives
from ui.notifications import show_recommendation, show_uninstall_success
from utils.winget_wrapper import install_app

logger = logging.getLogger(__name__)

BG = "#1e1e2e"
FG = "#cdd6f4"
ACCENT = "#89b4fa"
RED = "#f38ba8"
GREEN = "#a6e3a1"
SURFACE = "#313244"
HEADER_BG = "#181825"


class Dashboard:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} - ダッシュボード [{DEVICE_ID}]")
        self.root.geometry("960x640")
        self.root.configure(bg=BG)
        self.root.minsize(800, 500)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background=BG, foreground=FG)
        style.configure("TNotebook", background=BG)
        style.configure("TNotebook.Tab", background=SURFACE, foreground=FG,
                         padding=[12, 6])
        style.map("TNotebook.Tab",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", "#1e1e2e")])
        style.configure("Treeview", background=SURFACE, foreground=FG,
                         fieldbackground=SURFACE, rowheight=28)
        style.configure("Treeview.Heading", background=HEADER_BG,
                         foreground=ACCENT)
        style.configure("TButton", background=ACCENT, foreground="#1e1e2e",
                         padding=[8, 4])
        style.configure("Danger.TButton", background=RED, foreground="#1e1e2e")
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=FG)
        style.configure("TLabelframe", background=BG, foreground=FG)
        style.configure("TLabelframe.Label", background=BG, foreground=ACCENT)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self._build_usage_tab()
        self._build_least_used_tab()
        self._build_deletion_log_tab()
        self._build_settings_tab()

    # --- Tab 1: Usage Overview ---
    def _build_usage_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="使用状況")

        toolbar = ttk.Frame(frame)
        toolbar.pack(fill=tk.X, padx=8, pady=4)

        ttk.Label(toolbar, text="期間:").pack(side=tk.LEFT, padx=(0, 4))
        self.period_var = tk.StringVar(value="30")
        period_combo = ttk.Combobox(toolbar, textvariable=self.period_var,
                                     values=["7", "14", "30", "90"],
                                     width=6, state="readonly")
        period_combo.pack(side=tk.LEFT)
        ttk.Label(toolbar, text="日間").pack(side=tk.LEFT, padx=(2, 8))

        ttk.Button(toolbar, text="更新",
                   command=self._refresh_usage).pack(side=tk.LEFT)

        # Bar chart canvas
        self.chart_canvas = tk.Canvas(frame, bg=SURFACE, height=300,
                                       highlightthickness=0)
        self.chart_canvas.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        # Table
        cols = ("rank", "app", "foreground", "launches", "score")
        self.usage_tree = ttk.Treeview(frame, columns=cols, show="headings",
                                        height=8)
        self.usage_tree.heading("rank", text="#")
        self.usage_tree.heading("app", text="アプリ名")
        self.usage_tree.heading("foreground", text="フォアグラウンド時間")
        self.usage_tree.heading("launches", text="検出回数")
        self.usage_tree.heading("score", text="スコア")
        self.usage_tree.column("rank", width=40, anchor="center")
        self.usage_tree.column("app", width=250)
        self.usage_tree.column("foreground", width=150, anchor="center")
        self.usage_tree.column("launches", width=100, anchor="center")
        self.usage_tree.column("score", width=80, anchor="center")
        self.usage_tree.pack(fill=tk.BOTH, padx=8, pady=(0, 8))

    def _refresh_usage(self):
        days = int(self.period_var.get())
        top = get_top_apps(n=20, days=days)

        # Update table
        for item in self.usage_tree.get_children():
            self.usage_tree.delete(item)
        for app in top:
            self.usage_tree.insert("", "end", values=(
                app["rank"],
                app["process_name"],
                format_duration(app["total_foreground_seconds"]),
                app["total_launches"],
                app["score"],
            ))

        # Update bar chart
        self._draw_chart(top[:15])

    def _draw_chart(self, apps):
        self.chart_canvas.delete("all")
        if not apps:
            self.chart_canvas.create_text(
                400, 150, text="データなし（トラッキングを開始してください）",
                fill=FG, font=("Segoe UI", 12))
            return

        w = self.chart_canvas.winfo_width() or 900
        h = self.chart_canvas.winfo_height() or 300
        margin_left = 160
        margin_right = 20
        margin_top = 20
        bar_height = max(10, (h - margin_top - 20) // len(apps) - 4)

        max_score = max(a["score"] for a in apps) or 1
        bar_area_width = w - margin_left - margin_right

        for i, app in enumerate(apps):
            y = margin_top + i * (bar_height + 4)
            bar_w = max(2, int((app["score"] / max_score) * bar_area_width))

            # App name
            self.chart_canvas.create_text(
                margin_left - 8, y + bar_height // 2,
                text=app["process_name"][:20], anchor="e",
                fill=FG, font=("Segoe UI", 9))

            # Bar
            color = ACCENT if i < 5 else "#585b70"
            self.chart_canvas.create_rectangle(
                margin_left, y, margin_left + bar_w, y + bar_height,
                fill=color, outline="")

            # Score label
            self.chart_canvas.create_text(
                margin_left + bar_w + 6, y + bar_height // 2,
                text=str(app["score"]), anchor="w",
                fill=FG, font=("Segoe UI", 8))

    # --- Tab 2: Least Used ---
    def _build_least_used_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="未使用アプリ")

        toolbar = ttk.Frame(frame)
        toolbar.pack(fill=tk.X, padx=8, pady=4)
        ttk.Button(toolbar, text="スキャン",
                   command=self._refresh_least_used).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="選択をアンインストール",
                   command=self._uninstall_selected,
                   style="Danger.TButton").pack(side=tk.LEFT, padx=8)
        ttk.Button(toolbar, text="代替アプリを探す",
                   command=self._show_alternatives).pack(side=tk.LEFT)

        cols = ("app", "winget_id", "foreground", "score", "alternative")
        self.least_tree = ttk.Treeview(frame, columns=cols, show="headings",
                                        height=15)
        self.least_tree.heading("app", text="アプリ名")
        self.least_tree.heading("winget_id", text="Winget ID")
        self.least_tree.heading("foreground", text="使用時間")
        self.least_tree.heading("score", text="スコア")
        self.least_tree.heading("alternative", text="代替候補")
        self.least_tree.column("app", width=200)
        self.least_tree.column("winget_id", width=200)
        self.least_tree.column("foreground", width=120, anchor="center")
        self.least_tree.column("score", width=80, anchor="center")
        self.least_tree.column("alternative", width=200)

        scrollbar = ttk.Scrollbar(frame, orient="vertical",
                                   command=self.least_tree.yview)
        self.least_tree.configure(yscrollcommand=scrollbar.set)
        self.least_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                              padx=(8, 0), pady=(0, 8))
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 8), pady=(0, 8))

    def _refresh_least_used(self):
        for item in self.least_tree.get_children():
            self.least_tree.delete(item)

        # Run scan in background
        def scan():
            scan_installed_apps()
            bottom = get_bottom_apps(n=50, days=30)
            installed = get_all_apps()
            installed_names = [a["app_name"] for a in installed]

            self.root.after(0, lambda: self._populate_least_used(
                bottom, installed_names))

        threading.Thread(target=scan, daemon=True).start()

    def _populate_least_used(self, bottom, installed_names):
        for app in bottom:
            alts = get_alternatives(app["process_name"])
            alt_text = alts[0]["name"] if alts else ""
            self.least_tree.insert("", "end", values=(
                app["process_name"],
                "",
                format_duration(app["total_foreground_seconds"]),
                app["score"],
                alt_text,
            ))

    def _uninstall_selected(self):
        selected = self.least_tree.selection()
        if not selected:
            messagebox.showinfo("AppPulse", "アプリを選択してください")
            return

        app_name = self.least_tree.item(selected[0])["values"][0]
        winget_id = self.least_tree.item(selected[0])["values"][1] or None

        if is_blocked(winget_id, app_name):
            messagebox.showerror(
                "AppPulse",
                f"{app_name} はシステム重要アプリのため削除できません")
            return

        # 拒否回数を取得して警告レベルを決定
        rejection_count = get_rejection_count(app_name, DEVICE_ID)
        vals = self.least_tree.item(selected[0])["values"]
        fg_time = vals[2] if len(vals) > 2 else "不明"
        score = vals[3] if len(vals) > 3 else "不明"
        alt_name = vals[4] if len(vals) > 4 and vals[4] else "なし"

        # 警告レベルに応じたメッセージ
        if rejection_count == 0:
            severity = "通常確認"
            extra = ""
        elif rejection_count <= 2:
            severity = "注意"
            extra = (f"\n\n[注意] 過去に{rejection_count}回、"
                     f"このアプリの削除を見送っています。")
        elif rejection_count <= 5:
            severity = "警告"
            extra = (f"\n\n[警告] 過去に{rejection_count}回、"
                     f"削除を見送っています。\n"
                     f"本当に必要なアプリか再検討してください。")
        else:
            severity = "重要警告"
            extra = (f"\n\n[重要警告] 過去に{rejection_count}回、"
                     f"削除を見送っています。\n"
                     f"何度も削除候補に挙がっています。\n"
                     f"使っていないなら、今回こそ削除を検討してください。")

        confirm_msg = (
            f"以下のアプリをアンインストールしますか？\n\n"
            f"  アプリ名: {app_name}\n"
            f"  使用時間: {fg_time}\n"
            f"  スコア: {score}\n"
            f"  代替候補: {alt_name}\n"
            f"  過去の見送り回数: {rejection_count}回"
            f"{extra}\n\n"
            f"この操作は元に戻せません。\n"
            f"削除ログは自動的に記録されます。"
        )
        if not messagebox.askyesno(f"アンインストール確認 [{severity}]",
                                   confirm_msg):
            insert_rejection(app_name, DEVICE_ID, stage="first")
            return

        # 二重確認（警告レベルが高いほどメッセージも強く）
        if rejection_count > 5:
            final_msg = (
                f"[最終確認 - 重要警告]\n\n"
                f"{app_name} を削除します。\n"
                f"過去{rejection_count}回見送っていますが、"
                f"今回は本当に実行しますか？")
        elif rejection_count > 2:
            final_msg = (
                f"[最終確認 - 警告]\n\n"
                f"本当に {app_name} を削除しますか？\n"
                f"「はい」を押すとアンインストールを実行します。")
        else:
            final_msg = (
                f"本当に {app_name} を削除しますか？\n"
                f"「はい」を押すとアンインストールを実行します。")

        if not messagebox.askyesno("最終確認", final_msg):
            insert_rejection(app_name, DEVICE_ID, stage="final")
            return

        def do_uninstall():
            success, msg = uninstall(
                app_name, winget_id=winget_id, reason="least_used",
                confirmed=True)
            if success:
                show_uninstall_success(app_name)
            self.root.after(0, lambda: messagebox.showinfo("AppPulse", msg))
            self.root.after(0, self._refresh_least_used)

        threading.Thread(target=do_uninstall, daemon=True).start()

    def _show_alternatives(self):
        selected = self.least_tree.selection()
        if not selected:
            messagebox.showinfo("AppPulse", "アプリを選択してください")
            return

        app_name = self.least_tree.item(selected[0])["values"][0]
        alts = get_alternatives(app_name)

        if not alts:
            messagebox.showinfo("AppPulse",
                                f"{app_name} の代替アプリは登録されていません")
            return

        # Show alternatives in popup
        win = tk.Toplevel(self.root)
        win.title(f"{app_name} の代替アプリ")
        win.geometry("500x300")
        win.configure(bg=BG)

        ttk.Label(win, text=f"{app_name} の代替候補:",
                  font=("Segoe UI", 12, "bold")).pack(padx=16, pady=(16, 8))

        for alt in alts:
            alt_frame = ttk.Frame(win)
            alt_frame.pack(fill=tk.X, padx=16, pady=4)

            ttk.Label(alt_frame, text=alt["name"],
                      font=("Segoe UI", 11, "bold")).pack(
                          side=tk.LEFT, padx=(0, 8))
            ttk.Label(alt_frame, text=alt["reason"]).pack(
                side=tk.LEFT, fill=tk.X, expand=True)

            if alt.get("winget_id"):
                wid = alt["winget_id"]

                def make_install(w=wid, n=alt["name"]):
                    def do_install():
                        if messagebox.askyesno(
                                "インストール確認",
                                f"{n} をインストールしますか？"):
                            threading.Thread(
                                target=lambda: self._install_alt(w, n),
                                daemon=True).start()
                    return do_install

                ttk.Button(alt_frame, text="インストール",
                           command=make_install()).pack(side=tk.RIGHT)

    def _install_alt(self, winget_id, name):
        success, output = install_app(winget_id)
        msg = (f"{name} のインストールが完了しました"
               if success else f"インストール失敗:\n{output[:200]}")
        self.root.after(0, lambda: messagebox.showinfo("AppPulse", msg))

    # --- Tab 3: Deletion Log ---
    def _build_deletion_log_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="削除ログ")

        toolbar = ttk.Frame(frame)
        toolbar.pack(fill=tk.X, padx=8, pady=4)
        ttk.Button(toolbar, text="更新",
                   command=self._refresh_deletion_log).pack(side=tk.LEFT)

        cols = ("timestamp", "app", "reason", "method", "result")
        self.del_tree = ttk.Treeview(frame, columns=cols, show="headings",
                                      height=15)
        self.del_tree.heading("timestamp", text="日時")
        self.del_tree.heading("app", text="アプリ名")
        self.del_tree.heading("reason", text="理由")
        self.del_tree.heading("method", text="方法")
        self.del_tree.heading("result", text="結果")
        self.del_tree.column("timestamp", width=160)
        self.del_tree.column("app", width=220)
        self.del_tree.column("reason", width=120)
        self.del_tree.column("method", width=120)
        self.del_tree.column("result", width=80, anchor="center")
        self.del_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

    def _refresh_deletion_log(self):
        for item in self.del_tree.get_children():
            self.del_tree.delete(item)

        for row in get_deletion_log():
            self.del_tree.insert("", "end", values=(
                row["timestamp"][:16] if row["timestamp"] else "",
                row["app_name"],
                row["reason"] or "",
                row["uninstall_method"] or "",
                "成功" if row["success"] else "失敗",
            ))

    # --- Tab 4: Settings ---
    def _build_settings_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="設定")

        info_frame = ttk.LabelFrame(frame, text="デバイス情報")
        info_frame.pack(fill=tk.X, padx=16, pady=8)

        ttk.Label(info_frame,
                  text=f"デバイス名: {DEVICE_ID}").pack(
                      anchor="w", padx=12, pady=4)

        from storage.sync import get_sync_status
        status = get_sync_status()
        sync_text = ("同期: 有効" if status["available"]
                     else "同期: OneDriveフォルダが見つかりません")
        ttk.Label(info_frame, text=sync_text).pack(
            anchor="w", padx=12, pady=4)

        if status["available"]:
            for dev in status["devices"]:
                ttk.Label(info_frame,
                          text=f"  {dev['device_id']}: "
                               f"アプリ{dev['app_count']}件 "
                               f"(最終同期: {dev['exported_at'][:16]})").pack(
                    anchor="w", padx=12, pady=2)

        actions_frame = ttk.LabelFrame(frame, text="アクション")
        actions_frame.pack(fill=tk.X, padx=16, pady=8)

        ttk.Button(actions_frame, text="手動同期",
                   command=self._manual_sync).pack(
                       anchor="w", padx=12, pady=4)
        ttk.Button(actions_frame, text="アプリ一覧を再スキャン",
                   command=self._rescan_apps).pack(
                       anchor="w", padx=12, pady=4)

    def _manual_sync(self):
        from storage.sync import export_stats
        try:
            path = export_stats()
            messagebox.showinfo("AppPulse", f"同期完了:\n{path}")
        except Exception as e:
            messagebox.showerror("AppPulse", f"同期失敗:\n{e}")

    def _rescan_apps(self):
        def scan():
            apps = scan_installed_apps()
            self.root.after(0, lambda: messagebox.showinfo(
                "AppPulse", f"{len(apps)} 件のアプリを検出しました"))

        threading.Thread(target=scan, daemon=True).start()

    def run(self):
        """Start the dashboard."""
        init_db()
        self._refresh_usage()
        self._refresh_deletion_log()
        self.root.mainloop()
