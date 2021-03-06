import sys
from datetime import datetime


class Settings:
    # These are defined in 2 places because the unpickled settings may be missing a property that's been added

    class_version: int = 1

    # Masto -> Twitter
    post_to_twitter = True
    post_private_to_twitter = False
    post_unlisted_to_twitter = False
    split_twitter_messages = True
    post_boosts_to_twitter = True
    # post_sensitive_behind_link = False
    # sensitive_link_text = '(NSFW Image)'

    # Twitter -> Masto
    post_to_mastodon = True
    post_rts_to_mastodon = True
    post_quotes_to_mastodon = True
    toot_visibility = 'public'
    tweets_behind_cw = False
    tweet_cw_text = "From birdsite"

    instagram_post_to_twitter = False
    instagram_post_to_mastodon = False

    def __init__(self):

        self.version = self.__class__.class_version

        self.post_to_twitter = True  # This means post public toots
        self.post_private_to_twitter = False
        self.post_unlisted_to_twitter = False
        self.split_twitter_messages = True
        self.post_boosts_to_twitter = True
        # self.post_sensitive_behind_link = False
        # self.sensitive_link_text = '(NSFW Image)'

        self.post_to_mastodon = True  # This means post non-RT tweets
        self.post_rts_to_mastodon = True
        self.post_quotes_to_mastodon = True
        self.toot_visibility = 'public'
        self.tweets_behind_cw = False
        self.tweet_cw_text = "From birdsite"

        self.instagram_post_to_twitter = False
        self.instagram_post_to_mastodon = False

    def check_for_upgrade(self):
        if not hasattr(self, 'version'):
            self.version = 0

        if self.version != self.class_version:
            self.upgrade()
            return True
        else:
            return False

    def upgrade(self):
        version = self.version
        print(f'upgrade from version {self.version}')

        if version < 1:
            self.version = 1
            print(f'upgrade to version {self.version}')
            self.post_sensitive_behind_link = False
            self.sensitive_link_text = '(NSFW Image)'

    def merge(self, old_settings):
        for k, v in old_settings.__dict__.items():
            print(k, v)
            setattr(self, k, v)

    @property
    def post_to_twitter_enabled(self):
        return self.post_to_twitter or \
               self.post_private_to_twitter or \
               self.post_unlisted_to_twitter or \
               self.post_boosts_to_twitter

    @property
    def post_to_mastodon_enabled(self):
        return self.post_to_mastodon or \
               self.post_rts_to_mastodon


if __name__ == '__main__':
    import os
    import importlib
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from pprint import pprint as pp

    from moa.models import Bridge

    moa_config = os.environ.get('MOA_CONFIG', 'DevelopmentConfig')
    config = getattr(importlib.import_module('config'), moa_config)

    engine = create_engine(config.SQLALCHEMY_DATABASE_URI)
    engine.connect()
    session = Session(engine)

    if sys.argv[1]:
        bridge = session.query(Bridge).filter_by(id=sys.argv[1]).first()

        s = bridge.settings
        # pp(s.__dict__)

        if s.check_for_upgrade():
            new_settings = Settings()
            new_settings.merge(s)
            bridge.settings = new_settings
            # pp(bridge.settings.__dict__)

            session.commit()
    else:
        bridges = session.query(Bridge).all()

        for bridge in bridges:
            s = bridge.settings

            if s.check_for_upgrade():
                # pp(s.__dict__)
                new_settings = Settings()
                new_settings.merge(s)
                bridge.settings = new_settings
                session.commit()

    session.close()
