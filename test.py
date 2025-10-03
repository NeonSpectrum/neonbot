import asyncio


async def check_ip_online(ip_address: str, count: int = 1, timeout: int = 5) -> bool:
    command = ['ping', '-c', str(count), '-W', str(timeout), ip_address]

    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        returncode = await process.wait()

        print(returncode == 0)

    except FileNotFoundError:
        return False
    except Exception as e:
        return


asyncio.run(check_ip_online('37.187.250.67'))
