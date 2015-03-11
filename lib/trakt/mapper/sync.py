from trakt.mapper.core.base import Mapper

import logging
from trakt.objects import Season, Episode

log = logging.getLogger(__name__)


class SyncMapper(Mapper):
    @classmethod
    def process(cls, store, items, media, **kwargs):
        if not media:
            return ValueError()

        func = getattr(cls, media)

        if not func:
            raise ValueError('Unknown media type: %r', media)

        return func(store, items, **kwargs)

    #
    # Movie
    #

    @classmethod
    def movies(cls, store, items, **kwargs):
        return cls.map_items(store, items, cls.movie, **kwargs)

    @classmethod
    def movie(cls, store, item, **kwargs):
        movie = cls.map_item(store, item, 'movie', **kwargs)

        # Update with root info
        if 'movie' in item:
            movie.update(item)

        return movie

    #
    # Show
    #

    @classmethod
    def shows(cls, store, items, **kwargs):
        return cls.map_items(store, items, cls.show, **kwargs)

    @classmethod
    def show(cls, store, item, **kwargs):
        show = cls.map_item(store, item, 'show', **kwargs)

        # Update with root info
        if 'show' in item:
            show.update(item)

        # Process any episodes in the item
        for i_season in item.get('seasons', []):
            season_num = i_season.get('number')

            season = cls.show_season(show, season_num, **kwargs)

            for i_episode in i_season.get('episodes', []):
                episode_num = i_episode.get('number')

                cls.show_episode(season, episode_num, i_episode, **kwargs)

        return show

    @staticmethod
    def show_season(show, pk, item=None, **kwargs):
        if pk not in show.seasons:
            show.seasons[pk] = Season.create([pk], item, **kwargs)
        else:
            show.seasons[pk].update(item, **kwargs)

        return show.seasons[pk]

    @staticmethod
    def show_episode(season, pk, item=None, **kwargs):
        if pk not in season.episodes:
            season.episodes[pk] = Episode.create([(season.pk, pk)], item, **kwargs)
        else:
            season.episodes[pk].update(item, **kwargs)

        if item and 'episode' in item:
            season.episodes[pk].update(item['episode'])

        return season.episodes[pk]

    #
    # Episode
    #

    @classmethod
    def episodes(cls, store, items, **kwargs):
        return cls.map_items(store, items, cls.episode, **kwargs)

    @classmethod
    def episode(cls, store, item, **kwargs):
        i_episode = item.get('episode', {})

        season_num = i_episode.get('season')
        episode_num = i_episode.get('number')

        # Build `show`
        show = cls.show(store, item['show'])

        if show is None:
            # Unable to create show
            return None

        # Build `season`
        season = cls.show_season(show, season_num, **kwargs)

        # Build `episode`
        episode = cls.show_episode(season, episode_num, item, **kwargs)

        return episode

    #
    # Helpers
    #

    @classmethod
    def map_items(cls, store, items, func, **kwargs):
        if store is None:
            store = {}

        for item in items:
            result = func(store, item, **kwargs)

            if result is None:
                log.warn('Unable to map item: %s', item)

        return store

    @classmethod
    def map_item(cls, store, item, media, **kwargs):
        if media in item:
            i_data = item[media]
        else:
            i_data = item

        pk, keys = cls.get_ids(media, i_data)

        if pk is None:
            # Item has no keys
            return None

        if pk not in store:
            # Create new item
            store[pk] = cls.create(media, i_data, keys, **kwargs)
        else:
            # Update existing item
            store[pk].update(i_data, **kwargs)

        return store[pk]
