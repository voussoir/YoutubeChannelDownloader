import apiclient.discovery
import datetime
import logging
import isodate

from . import helpers

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)
logging.getLogger('googleapiclient.discovery').setLevel(logging.WARNING)
logging.getLogger('requests.packages.urllib3.connectionpool').setLevel(logging.WARNING)
logging.getLogger('requests.packages.urllib3.util.retry').setLevel(logging.WARNING)


class VideoNotFound(Exception):
    pass

class Video:
    def __init__(self, data):
        self.id = data['id']

        snippet = data['snippet']
        content_details = data['contentDetails']
        statistics = data['statistics']

        self.title = snippet['title'] or '[untitled]'
        self.description = snippet['description']
        self.author_id = snippet['channelId']
        self.author_name = snippet['channelTitle']
        # Something like '2016-10-01T21:00:01'
        self.published_string = snippet['publishedAt']
        published = snippet['publishedAt'].split('.')[0]
        published = datetime.datetime.strptime(published, '%Y-%m-%dT%H:%M:%S')
        self.published = published.timestamp()

        self.duration = isodate.parse_duration(content_details['duration']).seconds
        self.views = statistics['viewCount']

        thumbnails = snippet['thumbnails']
        best_thumbnail = max(thumbnails, key=lambda x: thumbnails[x]['width'] * thumbnails[x]['height'])
        self.thumbnail = thumbnails[best_thumbnail]

    def __str__(self):
        return 'Video:%s' % self.id


class Youtube:
    def __init__(self, key):
        youtube = apiclient.discovery.build(
            developerKey=key,
            serviceName='youtube',
            version='v3',
        )
        self.youtube = youtube

    def get_user_id(self, username):
        user = self.youtube.channels().list(part='snippet', forUsername=username).execute()
        return user['items'][0]['id']

    def get_user_name(self, uid):
        user = self.youtube.channels().list(part='snippet', id=uid).execute()
        return user['items'][0]['snippet']['title']

    def _iter_playlist(self, playlist_id):
        page_token = None
        while True:
            response = self.youtube.playlistItems().list(
                maxResults=50,
                pageToken=page_token,
                part='contentDetails',
                playlistId=playlist_id,
            ).execute()
            page_token = response.get('nextPageToken', None)
            video_ids = [item['contentDetails']['videoId'] for item in response['items']]
            videos = self.get_video(video_ids)
            videos.sort(key=lambda x: x.published, reverse=True)

            for video in videos:
                yield video

            if page_token is None:
                break

    def get_playlist_videos(self, playlist_id):
        yield from self._iter_playlist(playlist_id)

    def get_user_videos(self, username=None, uid=None):
        if username:
            user = self.youtube.channels().list(part='contentDetails', forUsername=username).execute()
        else:
            user = self.youtube.channels().list(part='contentDetails', id=uid).execute()
        upload_playlist_id = user['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        yield from self._iter_playlist(upload_playlist_id)

    def get_related_videos(self, video_id, count=50):
        if isinstance(video_id, Video):
            video_id = video_id.id

        results = self.youtube.search().list(
            part='id',
            relatedToVideoId=video_id,
            type='video',
            maxResults=count,
        ).execute()
        videos = []
        related = [rel['id']['videoId'] for rel in results['items']]
        videos = self.get_video(related)
        return videos

    def get_video(self, video_ids):
        if isinstance(video_ids, str):
            singular = True
            video_ids = [video_ids]
        else:
            singular = False

        snippets = []
        chunks = helpers.chunk_sequence(video_ids, 50)
        for chunk in chunks:
            chunk = ','.join(chunk)
            data = self.youtube.videos().list(part='id,contentDetails,snippet,statistics', id=chunk).execute()
            items = data['items']
            snippets.extend(items)
        videos = []
        broken = []
        for snippet in snippets:
            try:
                videos.append(Video(snippet))
            except KeyError:
                broken.append(snippet)
        if broken:
            print('broken:', broken)
        if singular:
            if len(videos) == 1:
                return videos[0]
            elif len(videos) == 0:
                raise VideoNotFound(video_ids[0])
        return videos
