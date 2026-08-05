from bot.core.config import load_config


def main() -> None:

    config = load_config()

    print("=" * 41)
    print(" NIKKE Union Raid Bot v0.1.0")
    print("=" * 41)

    print(
        f"Discord Token : {'Loaded' if config.discord_token else 'Not Found'}"
    )

    print(
        f"Guild ID      : {'Loaded' if config.guild_id else 'Not Found'}"
    )


if __name__ == "__main__":
    main()