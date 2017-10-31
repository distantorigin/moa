import os
from flask import Flask
from flask import g, session, request, url_for, flash
from flask import redirect, render_template
from flask_oauthlib.client import OAuth
# from flask_sqlalchemy import SQLAlchemy
from mastodon import Mastodon
from models import db, Bridge, MastodonHost


app = Flask(__name__)
app.config.from_object('config.DevelopmentConfig')
db.init_app(app)
oauth = OAuth(app)

twitter = oauth.remote_app(
    'twitter',
    consumer_key=app.config['TWITTER_CONSUMER_KEY'],
    consumer_secret=app.config['TWITTER_CONSUMER_SECRET'],
    base_url='https://api.twitter.com/1.1/',
    request_token_url='https://api.twitter.com/oauth/request_token',
    access_token_url='https://api.twitter.com/oauth/access_token',
    authorize_url='https://api.twitter.com/oauth/authorize'
)

app.logger.debug(twitter)

# @twitter.tokengetter
# def get_twitter_token():
#     if 'twitter' in session:
#         resp = session['twitter']
#         return resp['oauth_token'], resp['oauth_token_secret']


@app.route('/')
def index():

    return render_template('index.html.j2')


@app.before_request
def before_request():
    g.t_user = None
    g.m_user = None

    if 'twitter' in session:
        g.t_user = session['twitter']

    if 'mastodon' in session:
        g.m_user = session['mastodon']

    app.logger.info(session)

#
# Twitter
#


@app.route('/twitter_login')
def twitter_login():
    callback_url = url_for('twitter_oauthorized', next=request.args.get('next'))

    app.logger.debug(callback_url)

    return twitter.authorize(callback=callback_url)


@app.route('/twitter_oauthorized')
def twitter_oauthorized():
    resp = twitter.authorized_response()
    if resp is None:
        flash('You denied the request to sign in.')
    else:
        session['twitter'] = resp

    return redirect(url_for('index'))

#
# Mastodon
#


def get_or_create_host(hostname):

    mastodonhost = MastodonHost.query.filter_by(hostname=hostname).first()

    if not mastodonhost:

        client_id, client_secret = Mastodon.create_app(
            "Moa",
            scopes=["read", "write"],
            api_base_url=hostname,
            website="https://moa.social/",
            redirect_uris=url_for("mastodon_oauthorized", _external=True)

        )
        app.logger.info(f"New host created for {host} {client_id} {client_secret}")

        mastodonhost = MastodonHost(hostname=hostname,
                                    client_id=client_id,
                                    client_secret=client_secret)
        db.session.add(mastodonhost)
        db.session.commit()

    return mastodonhost


@app.route('/mastodon_login', methods=['POST'])
def mastodon_login():

    user_id = request.form.get('username')

    if "@" not in user_id:
        flash('Invalid Mastodon ID')
        return redirect(url_for('index'))

    username, host = user_id.split('@')

    session['mastodon_host'] = host

    # Do we have an app registered with this instance?

    mastodonhost = get_or_create_host(host)

    mastodon_api = Mastodon(
        client_id=mastodonhost.client_id,
        client_secret=mastodonhost.client_secret,
        api_base_url=mastodonhost.hostname,
        debug_requests=True
    )

    return redirect(
        mastodon_api.auth_request_url(
            scopes=['read', 'write'],
            redirect_uris=url_for("mastodon_oauthorized", _external=True)
        )
    )


@app.route('/mastodon_oauthorized')
def mastodon_oauthorized():

    authorization_code = request.args.get('code')

    if authorization_code is None:
        flash('You denied the request to sign in to Mastodon.')
    else:

        mastodonhost = get_or_create_host(session['mastodon_host'])

        mastodon_api = Mastodon(
            client_id=mastodonhost.client_id,
            client_secret=mastodonhost.client_secret,
            api_base_url=mastodonhost.hostname,
            debug_requests=True
        )

        access_code = mastodon_api.log_in(
            code=authorization_code,
            scopes=["read", "write"],
            redirect_uri=url_for("mastodon_oauthorized", _external=True)
        )

        data = {'mastodon_access_code': access_code}
        mastodon_api.access_code = access_code

        data['username'] = mastodon_api.account_verify_credentials()["username"]

        session['mastodon'] = data

    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    session.pop('twitter', None)
    session.pop('mastodon', None)
    return redirect(url_for('index'))


if __name__ == '__main__':

    if not os.path.isfile('/tmp/test.db'):
        with app.app_context():
            db.create_all()
    app.run()
