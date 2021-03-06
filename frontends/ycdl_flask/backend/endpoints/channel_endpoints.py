import flask; from flask import request
import itertools
import traceback

from voussoirkit import flasktools

import ycdl

from .. import common

site = common.site

@site.route('/all_channels.json')
def get_all_channel_names():
    all_channels = {channel.id: channel.name for channel in common.ycdldb.get_channels()}
    response = {'channels': all_channels}
    return flasktools.make_json_response(response)

@site.route('/channels')
def get_channels():
    channels = common.ycdldb.get_channels()
    return flask.render_template('channels.html', channels=channels)

@site.route('/videos')
@site.route('/watch')
@site.route('/videos/<state>')
@site.route('/channel/<channel_id>')
@site.route('/channel/<channel_id>/<state>')
def get_channel(channel_id=None, state=None):
    if channel_id is not None:
        common.ycdldb.add_channel(channel_id)
        try:
            channel = common.ycdldb.get_channel(channel_id)
        except ycdl.exceptions.NoSuchChannel:
            flask.abort(404)
    else:
        channel = None

    orderby = request.args.get('orderby', None)

    video_id = request.args.get('v', '')
    if video_id:
        common.ycdldb.insert_video(video_id)
        videos = [common.ycdldb.get_video(video_id)]
    else:
        videos = common.ycdldb.get_videos(
            channel_id=channel_id,
            state=state,
            orderby=orderby,
        )

    search_terms = request.args.get('q', '').lower().strip().replace('+', ' ').split()
    if search_terms:
        videos = (v for v in videos if all(term in v.title.lower() for term in search_terms))

    limit = request.args.get('limit', None)
    if limit is not None:
        try:
            limit = int(limit)
            videos = itertools.islice(videos, limit)
        except ValueError:
            pass

    videos = list(videos)

    all_states = common.ycdldb.get_all_states()

    return flask.render_template(
        'channel.html',
        all_states=all_states,
        channel=channel,
        state=state,
        orderby=orderby,
        videos=videos,
    )

@site.route('/add_channel', methods=['POST'])
def post_add_channel():
    channel_id = request.form.get('channel_id', '')
    channel_id = channel_id.strip()
    if not channel_id:
        flask.abort(400)
    if not (len(channel_id) == 24 and channel_id.startswith('UC')):
        # It seems they have given us a username instead.
        try:
            channel_id = common.ycdldb.youtube.get_user_id(username=channel_id)
        except ycdl.ytapi.ChannelNotFound:
            return flasktools.make_json_response({}, status=404)

    channel = common.ycdldb.add_channel(channel_id, get_videos=True)
    return flasktools.make_json_response(channel.jsonify())

@site.route('/channel/<channel_id>/delete', methods=['POST'])
def post_delete_channel(channel_id):
    try:
        channel = common.ycdldb.get_channel(channel_id)
    except ycdl.exceptions.NoSuchChannel as exc:
        return flasktools.make_json_response(exc.jsonify(), status=404)

    channel.delete()
    return flasktools.make_json_response({})

@site.route('/channel/<channel_id>/refresh', methods=['POST'])
def post_refresh_channel(channel_id):
    force = request.form.get('force', False)
    force = ycdl.helpers.truthystring(force)
    try:
        channel = common.ycdldb.get_channel(channel_id)
    except ycdl.exceptions.NoSuchChannel as exc:
        return flasktools.make_json_response(exc.jsonify(), status=404)

    channel.refresh(force=force)
    return flasktools.make_json_response(channel.jsonify())

@site.route('/refresh_all_channels', methods=['POST'])
def post_refresh_all_channels():
    force = request.form.get('force', False)
    force = ycdl.helpers.truthystring(force)
    common.ycdldb.refresh_all_channels(force=force, skip_failures=True)
    return flasktools.make_json_response({})

@site.route('/channel/<channel_id>/set_automark', methods=['POST'])
def post_set_automark(channel_id):
    state = request.form['state']
    channel = common.ycdldb.get_channel(channel_id)

    try:
        channel.set_automark(state)
    except ycdl.exceptions.InvalidVideoState:
        flask.abort(400)

    return flasktools.make_json_response({})

@site.route('/channel/<channel_id>/set_queuefile_extension', methods=['POST'])
def post_set_queuefile_extension(channel_id):
    extension = request.form['extension']
    channel = common.ycdldb.get_channel(channel_id)

    channel.set_queuefile_extension(extension)

    return flasktools.make_json_response({})
