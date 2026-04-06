package com.apppulse.recommender

data class Alternative(
    val name: String,
    val packageId: String?,
    val reason: String,
)

/**
 * Android向け代替アプリDB。
 * パッケージ名をキーにしてPlay Storeの代替アプリを提案する。
 */
object AlternativesDb {

    private val db = mapOf(
        "com.google.android.apps.photos" to AppAlternatives("gallery", listOf(
            Alternative("Simple Gallery", "com.simplemobiletools.gallery.pro", "軽量・広告なし・オープンソース"),
            Alternative("Aves", "deckers.thibault.aves", "高機能ギャラリー、マップ表示対応"),
        )),
        "com.google.android.gm" to AppAlternatives("email", listOf(
            Alternative("K-9 Mail", "com.fsck.k9", "オープンソース、プライバシー重視"),
            Alternative("FairEmail", "eu.faircode.email", "プライバシーファースト"),
        )),
        "com.whatsapp" to AppAlternatives("messenger", listOf(
            Alternative("Signal", "org.thoughtcrime.securesms", "エンドツーエンド暗号化、プライバシー重視"),
            Alternative("Telegram", "org.telegram.messenger", "高速、クラウド同期、ボット対応"),
        )),
        "com.instagram.android" to AppAlternatives("social", listOf(
            Alternative("Pixelfed", null, "オープンソースの分散型Instagram代替"),
        )),
        "com.twitter.android" to AppAlternatives("social", listOf(
            Alternative("Mastodon", "org.joinmastodon.android", "分散型SNS、オープンソース"),
            Alternative("Bluesky", "xyz.blueskyweb.app", "分散型プロトコル"),
        )),
        "com.facebook.katana" to AppAlternatives("social", listOf(
            Alternative("Frost for Facebook", null, "軽量ラッパー"),
        )),
        "com.spotify.music" to AppAlternatives("music", listOf(
            Alternative("YouTube Music", "com.google.android.apps.youtube.music", "YouTube統合"),
            Alternative("Auxio", "org.oxycblt.auxio", "ローカル音楽再生、オープンソース"),
        )),
        "com.google.android.apps.maps" to AppAlternatives("navigation", listOf(
            Alternative("OsmAnd", "net.osmand", "オフライン地図、オープンソース"),
            Alternative("Organic Maps", "app.organicmaps", "軽量、プライバシー重視"),
        )),
        "com.brave.browser" to AppAlternatives("browser", listOf(
            Alternative("Firefox", "org.mozilla.firefox", "プライバシー重視、拡張機能対応"),
            Alternative("Vivaldi", "com.vivaldi.browser", "高カスタマイズ性"),
        )),
        "com.android.chrome" to AppAlternatives("browser", listOf(
            Alternative("Brave", "com.brave.browser", "広告ブロック内蔵"),
            Alternative("Firefox", "org.mozilla.firefox", "プライバシー重視"),
        )),
        "com.discord" to AppAlternatives("communication", listOf(
            Alternative("Element", "im.vector.app", "Matrixプロトコル、オープンソース"),
        )),
        "com.microsoft.teams" to AppAlternatives("communication", listOf(
            Alternative("Slack", "com.Slack", "チャンネルベース、統合豊富"),
        )),
        "com.adobe.reader" to AppAlternatives("pdf", listOf(
            Alternative("MJ PDF", "com.gitlab.nickmj.pdfviewer", "軽量PDFビューア"),
        )),
        "com.microsoft.office.outlook" to AppAlternatives("email", listOf(
            Alternative("K-9 Mail", "com.fsck.k9", "オープンソース"),
            Alternative("FairEmail", "eu.faircode.email", "プライバシーファースト"),
        )),
        "com.google.android.keep" to AppAlternatives("notes", listOf(
            Alternative("Obsidian", "md.obsidian", "ローカルファースト、Markdown"),
            Alternative("Joplin", "net.cozic.joplin", "オープンソース、E2E暗号化"),
        )),
    )

    fun getAlternatives(packageName: String): List<Alternative> =
        db[packageName]?.alternatives ?: emptyList()

    fun getCategory(packageName: String): String =
        db[packageName]?.category ?: "unknown"
}

private data class AppAlternatives(
    val category: String,
    val alternatives: List<Alternative>,
)
