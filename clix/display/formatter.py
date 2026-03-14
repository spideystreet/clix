"""Rich terminal formatting for tweets, users, and threads."""

from __future__ import annotations

from datetime import UTC, datetime

from rich.console import Console
from rich.markdown import Markdown as RichMarkdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from clix.models.dm import DMConversation, DMMessage
from clix.models.tweet import Tweet, TweetEngagement
from clix.models.user import User

console = Console()


def _relative_time(dt: datetime | None) -> str:
    """Format a datetime as relative time (e.g., '2h ago')."""
    if dt is None:
        return ""
    now = datetime.now(UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    diff = now - dt
    seconds = int(diff.total_seconds())

    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m"
    elif seconds < 86400:
        return f"{seconds // 3600}h"
    elif seconds < 604800:
        return f"{seconds // 86400}d"
    else:
        return dt.strftime("%b %d, %Y")


def _format_number(n: int) -> str:
    """Format large numbers (e.g., 1.2K, 3.4M)."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def _truncate(text: str, limit: int) -> str:
    """Truncate text to limit chars, appending '...' if needed."""
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text


def format_tweet(tweet: Tweet, show_engagement: bool = True, full_text: bool = False) -> Panel:
    """Format a single tweet as a rich Panel."""
    # Header: author info + time
    verified = " [blue]\u2713[/blue]" if tweet.author_verified else ""
    time_str = _relative_time(tweet.created_at)

    header = Text()
    header.append(tweet.author_name, style="bold white")
    header.append(f"{verified} ", style="blue")
    header.append(f"@{tweet.author_handle}", style="dim cyan")
    header.append(f" \u00b7 {time_str}", style="dim")

    # Retweet indicator
    if tweet.is_retweet and tweet.retweeted_by:
        rt_line = Text(f"\U0001f501 {tweet.retweeted_by} retweeted", style="dim green")
        console.print(rt_line)

    # Reply indicator
    subtitle = ""
    if tweet.reply_to_handle:
        subtitle = f"replying to @{tweet.reply_to_handle}"

    # Tweet text
    display_text = tweet.text if full_text else _truncate(tweet.text, 280)
    body = Text(display_text)

    # Media indicators
    media_text = ""
    if tweet.media:
        media_labels = []
        for m in tweet.media:
            if m.type == "photo":
                media_labels.append("\U0001f5bc\ufe0f photo")
            elif m.type == "video":
                media_labels.append("\U0001f3ac video")
            elif m.type == "animated_gif":
                media_labels.append("GIF")
        media_text = " ".join(media_labels)

    # Engagement stats
    engagement_line = Text()
    if show_engagement:
        e = tweet.engagement
        stats = []
        if e.replies:
            stats.append(f"\U0001f4ac {_format_number(e.replies)}")
        if e.retweets:
            stats.append(f"\U0001f501 {_format_number(e.retweets)}")
        if e.likes:
            stats.append(f"\u2764\ufe0f  {_format_number(e.likes)}")
        if e.bookmarks:
            stats.append(f"\U0001f516 {_format_number(e.bookmarks)}")
        if e.views:
            stats.append(f"\U0001f441\ufe0f  {_format_number(e.views)}")
        engagement_line = Text(" \u00b7 ".join(stats), style="dim")

    # Build panel content
    content = Text()
    content.append_text(body)
    if media_text:
        content.append(f"\n{media_text}", style="dim yellow")
    if tweet.quoted_tweet:
        content.append(f"\n\u250c\u2500 @{tweet.quoted_tweet.author_handle}: ", style="dim")
        quoted_text = (
            tweet.quoted_tweet.text if full_text else _truncate(tweet.quoted_tweet.text, 120)
        )
        content.append(quoted_text, style="dim italic")
    if show_engagement and engagement_line.plain:
        content.append("\n")
        content.append_text(engagement_line)

    return Panel(
        content,
        title=header,
        subtitle=subtitle if subtitle else None,
        subtitle_align="left",
        border_style="dim",
        padding=(0, 1),
    )


def format_tweet_list(
    tweets: list[Tweet], show_engagement: bool = True, full_text: bool = False
) -> None:
    """Print a list of tweets."""
    if not tweets:
        console.print("[dim]No tweets found.[/dim]")
        return

    for tweet in tweets:
        console.print(format_tweet(tweet, show_engagement, full_text=full_text))
        console.print()


def format_user(user: User) -> Panel:
    """Format a user profile as a rich Panel."""
    verified = " [blue]\u2713[/blue]" if user.verified else ""

    header = Text()
    header.append(user.name, style="bold white")
    header.append(verified)
    header.append(f" @{user.handle}", style="dim cyan")

    content = Text()

    if user.bio:
        content.append(user.bio)
        content.append("\n\n")

    # Stats table
    stats = Table(show_header=False, box=None, padding=(0, 2))
    stats.add_column(style="bold")
    stats.add_column(style="dim")
    stats.add_row(_format_number(user.following_count), "Following")
    stats.add_row(_format_number(user.followers_count), "Followers")
    stats.add_row(_format_number(user.tweet_count), "Tweets")

    details = []
    if user.location:
        details.append(f"\U0001f4cd {user.location}")
    if user.website:
        details.append(f"\U0001f517 {user.website}")
    if user.created_at:
        details.append(f"\U0001f4c5 Joined {user.created_at.strftime('%B %Y')}")

    if details:
        content.append("\n".join(details))
        content.append("\n\n")

    return Panel(
        content,
        title=header,
        border_style="cyan",
        padding=(1, 2),
    )


def format_thread(tweets: list[Tweet], focal_id: str | None = None) -> None:
    """Display a tweet thread as a tree."""
    if not tweets:
        console.print("[dim]No tweets in thread.[/dim]")
        return

    # Find the focal tweet (or first tweet)
    focal = None
    for t in tweets:
        if focal_id and t.id == focal_id:
            focal = t
            break
    if focal is None:
        focal = tweets[0]

    # Build reply tree
    tree = Tree(f"[bold]Thread[/bold] \u00b7 {len(tweets)} tweets")

    # Group by conversation structure
    replies_map: dict[str | None, list[Tweet]] = {}
    for t in tweets:
        parent = t.reply_to_id
        replies_map.setdefault(parent, []).append(t)

    def add_to_tree(node: Tree, tweet: Tweet) -> None:
        verified = " \u2713" if tweet.author_verified else ""
        label = Text()
        label.append(f"@{tweet.author_handle}{verified}", style="bold cyan")
        label.append(f" {_relative_time(tweet.created_at)}", style="dim")
        label.append(f"\n{tweet.text[:200]}", style="white")

        e = tweet.engagement
        if e.likes or e.retweets:
            stats = []
            if e.likes:
                stats.append(f"\u2764\ufe0f {_format_number(e.likes)}")
            if e.retweets:
                stats.append(f"\U0001f501 {_format_number(e.retweets)}")
            label.append(f"\n{' '.join(stats)}", style="dim")

        child = node.add(label)

        # Add replies to this tweet
        for reply in replies_map.get(tweet.id, []):
            add_to_tree(child, reply)

    # Start with focal tweet
    add_to_tree(tree, focal)

    # Add orphan replies (direct replies not connected to focal)
    for reply in replies_map.get(focal.id, []):
        if reply.id != focal.id:
            add_to_tree(tree, reply)

    console.print(tree)


def format_article(
    title: str,
    author: str,
    content_md: str,
    engagement: TweetEngagement | None = None,
) -> Panel:
    """Format a Twitter Article as a rich Panel with rendered Markdown."""
    # Build engagement line if provided
    engagement_text = ""
    if engagement:
        stats = []
        if engagement.likes:
            stats.append(f"\u2764\ufe0f  {_format_number(engagement.likes)}")
        if engagement.retweets:
            stats.append(f"\U0001f501 {_format_number(engagement.retweets)}")
        if engagement.bookmarks:
            stats.append(f"\U0001f516 {_format_number(engagement.bookmarks)}")
        if engagement.views:
            stats.append(f"\U0001f441\ufe0f  {_format_number(engagement.views)}")
        if stats:
            engagement_text = " \u00b7 ".join(stats)

    from rich.console import Group

    parts: list[object] = [RichMarkdown(content_md)]
    if engagement_text:
        parts.append(Text())
        parts.append(Text(engagement_text, style="dim"))

    header = Text()
    header.append(title or "Article", style="bold white")
    header.append(f" by @{author}", style="dim cyan")

    return Panel(
        Group(*parts),
        title=header,
        border_style="green",
        padding=(1, 2),
    )


def format_user_list(users: list[User]) -> None:
    """Print a list of users in a table."""
    if not users:
        console.print("[dim]No users found.[/dim]")
        return

    table = Table(title="Users", border_style="dim")
    table.add_column("Handle", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Followers", style="dim")
    table.add_column("Bio", style="dim", max_width=50)

    for user in users:
        verified = " \u2713" if user.verified else ""
        table.add_row(
            f"@{user.handle}",
            f"{user.name}{verified}",
            _format_number(user.followers_count),
            (user.bio[:50] + "...") if len(user.bio) > 50 else user.bio,
        )

    console.print(table)


def format_lists(lists: list[dict]) -> None:
    """Print a list of Twitter/X lists in a table."""
    if not lists:
        console.print("[dim]No lists found.[/dim]")
        return

    table = Table(title="Your Lists", border_style="dim")
    table.add_column("ID", style="dim")
    table.add_column("Name", style="cyan bold")
    table.add_column("Members", style="white", justify="right")
    table.add_column("Description", style="dim", max_width=50)

    for lst in lists:
        description = lst.get("description", "") or ""
        if len(description) > 50:
            description = description[:50] + "..."
        table.add_row(
            lst.get("id", ""),
            lst.get("name", ""),
            _format_number(lst.get("member_count", 0)),
            description,
        )

    console.print(table)


def format_scheduled_tweets(tweets: list[dict]) -> None:
    """Display scheduled tweets in a table."""
    if not tweets:
        console.print("[dim]No scheduled tweets.[/dim]")
        return

    table = Table(title="Scheduled Tweets", border_style="dim")
    table.add_column("ID", style="cyan")
    table.add_column("Text", style="white", max_width=50)
    table.add_column("Scheduled For", style="yellow")
    table.add_column("State", style="dim")

    for tweet in tweets:
        text = tweet.get("text", "")
        truncated = (text[:47] + "...") if len(text) > 50 else text

        execute_at = tweet.get("execute_at")
        if execute_at:
            scheduled_time = datetime.fromtimestamp(execute_at, tz=UTC).strftime(
                "%Y-%m-%d %H:%M UTC"
            )
        else:
            scheduled_time = "Unknown"

        table.add_row(
            tweet.get("id", ""),
            truncated,
            scheduled_time,
            tweet.get("state", ""),
        )

    console.print(table)


def format_dm_inbox(conversations: list[DMConversation]) -> None:
    """Display DM inbox as a table."""
    if not conversations:
        console.print("[dim]No conversations found.[/dim]")
        return

    table = Table(title="DM Inbox", border_style="dim")
    table.add_column("Participants", style="cyan")
    table.add_column("Last Message", style="white", max_width=60)
    table.add_column("Time", style="dim")

    for conv in conversations:
        handles = ", ".join(
            f"@{p.get('handle', '?')}" for p in conv.participants if p.get("handle")
        )
        if not handles:
            handles = conv.id

        msg_preview = conv.last_message[:60]
        if len(conv.last_message) > 60:
            msg_preview += "..."

        # Convert epoch ms to relative time
        time_str = ""
        if conv.last_message_time:
            try:
                ts = int(conv.last_message_time) / 1000
                dt = datetime.fromtimestamp(ts, tz=UTC)
                time_str = _relative_time(dt)
            except (ValueError, OSError):
                time_str = conv.last_message_time

        style = "bold" if conv.unread else ""
        table.add_row(handles, msg_preview, time_str, style=style)

    console.print(table)


def format_trends(trends: list[dict]) -> None:
    """Print trending topics as a rich Table."""
    if not trends:
        console.print("[dim]No trending topics found.[/dim]")
        return

    table = Table(title="Trending Topics", border_style="dim")
    table.add_column("#", style="bold", width=4)
    table.add_column("Topic", style="cyan")
    table.add_column("Tweets", style="white", justify="right")
    table.add_column("Context", style="dim", max_width=40)

    for i, trend in enumerate(trends, 1):
        tweet_count = trend.get("tweet_count")
        count_str = _format_number(tweet_count) if tweet_count else "-"
        context = trend.get("context", "") or ""
        table.add_row(str(i), trend["name"], count_str, context)

    console.print(table)


def format_dm_messages(messages: list[DMMessage]) -> None:
    """Display DM messages in chronological order."""
    if not messages:
        console.print("[dim]No messages found.[/dim]")
        return

    for msg in messages:
        # Convert epoch ms to relative time
        time_str = ""
        if msg.created_at:
            try:
                ts = int(msg.created_at) / 1000
                dt = datetime.fromtimestamp(ts, tz=UTC)
                time_str = _relative_time(dt)
            except (ValueError, OSError):
                time_str = msg.created_at

        sender = msg.sender_name or msg.sender_id
        header = Text()
        header.append(sender, style="bold cyan")
        header.append(f" {time_str}", style="dim")
        console.print(header)
        console.print(f"  {msg.text}")
        console.print()


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[green]\u2713[/green] {message}")


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[red]\u2717[/red] {message}", style="red")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[yellow]\u26a0[/yellow] {message}", style="yellow")
