from neonbot.classes.ytdl import Ytdl


class Youtube:
    def __init__(self):
        self.ytdl = Ytdl()

    async def get_info(self, value: str, process=False):
        return await self.ytdl.extract_info(value, process=process)

    def beautify_choices(self, data):
        return self.ytdl.parse_choices(data)

    def get_playlist(self, ytdl_list):
        info = []

        for entry in ytdl_list:
            info.append(entry)

        return info


youtube = Youtube()
