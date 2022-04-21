import discord


async def check_can_dm_user(user: discord.User) -> bool:
    """
    Checks if the user has a DM open.

    NOTE: This method has a 100% error rate, so it should not be used unless absolutely necessary.
    Repeated usage can lead to a discord api ban.
    """
    try:
        await user.send("")
    except discord.errors.Forbidden:
        return False
    except discord.errors.HTTPException as e:
        return "empty message" in e.text.lower()
    except discord.errors.DiscordException as e:
        raise e
