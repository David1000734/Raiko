class Reddit:
    __reddit_task = []
    'Background task fetching posts from Reddit.'

    __reddit_post = []
    'Most recent X post already made onto Discord.'

    def __init__(self):
        pass

    def get_post(self) -> list:
        return self.__reddit_post

    def get_task(self) -> list:
        return self.__reddit_task

    pass
