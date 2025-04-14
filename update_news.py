from main import init_db, parse_rss_feed, parse_telegram_channels, load_sources

init_db()
rss_sites, telegram_channels = load_sources()

for site in rss_sites:
    parse_rss_feed(site)

parse_telegram_channels(telegram_channels)
