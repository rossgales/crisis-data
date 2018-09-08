from celery.task.control import revoke
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
import re
import pytz

from django.utils import timezone
from dateutil.parser import *

from twdata import userdata
from .models import Event, CeleryTask, User, Relo, Tweet, Place, Hashtag, Url, Mention, Keyword
from .config import FRIENDS_THRESHOLD, FOLLOWERS_THRESHOLD, STATUSES_THRESHOLD, TAG_OCCURENCE_THRESHOLD, MENTION_OCCURENCE_THRESHOLD

from django.db import transaction
from django.db.models import Count


def update_screen_names(users=None):
    print('Updating Screen Names...')

    if users is None:
        users = list(User.objects.filter(user_class__gte=2).values_list('user_id', flat=True))
    length = len(users)
    chunk_size = 100 # Max of 100
    index = 0
    c = 0 # total changed
    deleted_users = list(users)

    # Requesting User objects in batches to minimise API limits
    while index < length:
        if length - index <= chunk_size:
            end = length
        else:
            end = index + chunk_size
        chunk = users[index:end]
        print("Length: {}, Chunk: {}:{}".format(length, index, end))
        #process chunk
        user_list = userdata.lookup_users(user_ids=chunk)
        if not user_list:
            # False returned if only dead users in list
            index += chunk_size
            continue
        for live_u in user_list:
            deleted_users.remove(int(live_u.id_str))
            u = User.objects.get(user_id=int(live_u.id_str))
            if live_u.screen_name != u.screen_name:
                print('New screen name for user: {} - {}.'.format(u.screen_name, live_u.screen_name))
                u.old_screen_name = u.screen_name
                u.screen_name = live_u.screen_name
                u.save()
                c += 1
        index += chunk_size

    for deleted_id in deleted_users:
        u = User.objects.get(user_id=deleted_id)
        if u.is_deleted == False:
            u.is_deleted = True
            u.is_deleted_observed = timezone.now()
            u.save()

    print('{} users changed names out of {} total.'.format(c, len(users)))
    print('{} deleted or suspended users.'.format(len(deleted_users)))
    return


def check_deleted_tweets(id_list=None):
    print('Checking existing Tweets for deletion...')

    if id_list is None:
        id_list = list(Tweet.objects.filter(data_source__gte=1).values_list('tweet_id', flat=True))

    length = len(id_list)
    chunk_size = 100 # Max of 100
    index = 0
    deleted_tweets = list(id_list)

    # Requesting Tweet objects in batches to minimise API limits
    while index < length:
        if length - index <= chunk_size:
            end = length
        else:
            end = index + chunk_size
        chunk = id_list[index:end]
        print("Length: {}, Chunk: {}:{}".format(length, index, end))
        #process chunk
        tweet_list = userdata.statuses_lookup(chunk)
        if not tweet_list:
            index += chunk_size
            continue
        for live_t in tweet_list:
            deleted_tweets.remove(int(live_t.id_str))
        index += chunk_size

    for deleted_id in deleted_tweets:
        t = Tweet.objects.get(tweet_id=deleted_id)
        if t.is_deleted == False:
            t.is_deleted = True
            t.is_deleted_observed = timezone.now()
            t.save()

    print('{} deleted or hidden Tweets of total: {}.'.format(len(deleted_tweets), length))
    return


def kill_celery_task(task_name):
    for t in CeleryTask.objects.filter(task_name=task_name):
        print('Killing task {}: {}'.format(task_name, t.celery_task_id))
        revoke(t.celery_task_id, terminate=True)
        t.delete()


def check_spam_account(user_data):
    # Reject users with high metrics - spam/celebrity/news accounts
    if user_data.followers_count > FOLLOWERS_THRESHOLD:
        return True
    if user_data.friends_count > FRIENDS_THRESHOLD:
        return True
    if user_data.statuses_count > STATUSES_THRESHOLD:
        return True
    else:
        return False


def update_tracked_tags():
    print('updating tracked tags')
    #If a hashtag appears in x% of tweets, add as a keyword to track.
    hashtags_with_counts = Hashtag.objects.all().annotate(tweet_count=Count('tweets__id'))
    tweet_count = len(Tweet.objects.all())
    threshold = (tweet_count*TAG_OCCURENCE_THRESHOLD)

    temp_dic = {}
    keywords = Keyword.objects.all().values_list('keyword', flat=True)

    for tag in hashtags_with_counts:
        if tag.hashtag not in keywords:
            temp_dic[tag.hashtag]=tag.tweet_count
        if tag.tweet_count > threshold:
            hashtag = '#' + tag.hashtag
            try:
                k = Keyword()
                k.keyword = hashtag.lower()
                k.created_at = timezone.now()
                k.save()
                print('Adding new hashtag to keyword list: {}'.format(hashtag))
            except:
                #print('Error keyword list: {} Likely already exists.'.format(hashtag))
                pass

    # Print most common tags
    top = sorted(temp_dic.items(), key=lambda x:x[1], reverse=True)[0:5]
    print(top)
    print('Total tweets: {}'.format(tweet_count))


def add_users_from_mentions():
    #If a mention appears in x% of tweets, add as a user_class=2. #TODO: Sould this use a different user_class?
    mentions_with_counts = Mention.objects.all().annotate(tweet_count=Count('tweets__id'))
    tweet_count = len(Tweet.objects.all())
    threshold = (tweet_count*MENTION_OCCURENCE_THRESHOLD)

    for user in mentions_with_counts:
        if user.tweet_count > threshold:
            print('Adding new user from mentions: {}'.format(user.mention))
            add_user(user_class=2, data_source=0, screen_name=user.mention)
    return


#@transaction.atomic
def add_user(user_class=0, user_data=None, data_source=0, **kwargs):
    # User exists at the user_class level
    if 'screen_name' in kwargs:
        screen_name=kwargs.get('screen_name')
        try:
            u = User.objects.get(screen_name=screen_name)
            if u.user_class >= user_class:
                print('User {} already exists.'.format(u.screen_name))
                if u.data_source < data_source:
                    u.data_source = data_source
                    u.save()
                return u
        except:
            pass
    # Get user_data if not supplied
    if not user_data:
        user_data=userdata.get_user(**kwargs)
    if check_spam_account(user_data):
        return False
    try:
        u # exists? i.e. made with screen_name call above.
    except:
        try:
            u = User.objects.get(user_id=int(user_data.id_str))
        except:
            u = User()
    # Check if user already exists class level. None is true if the user hasn't
    # been saved yet (i.e. created in this function)
    if not u.user_class == None and u.user_class >= user_class:
        print('User {} already exists.'.format(u.screen_name))
        if u.data_source < data_source:
            u.data_source = data_source
            u.save()
        return u

    # If timezone is an issue:
    u.added_at = timezone.now()
    try:
        tz_aware = timezone.make_aware(user_data.created_at, timezone=pytz.utc)
    except pytz.exceptions.AmbiguousTimeError:
        # Adding an hour to avoid DST ambiguity errors.
        time_adjusted = user_data.created_at + timedelta(minutes=60)
        tz_aware = timezone.make_aware(time_adjusted, timezone=pytz.utc)
    u.created_at = tz_aware

    u.default_profile = user_data.default_profile
    u.default_profile_image = user_data.default_profile_image
    u.description = user_data.description
    # u.entities = NOT IMPLEMENTED
    u.favourites_count = user_data.favourites_count
    u.followers_count = user_data.followers_count
    u.friends_count = user_data.friends_count
    u.geo_enabled = user_data.geo_enabled
    #u.has_extended_profile = user_data.has_extended_profile      # not returned in user object attached to Tweet, requires API request
    #u.is_translation_enabled = user_data.is_translation_enabled    # not returned in user object attached to Tweet, requires API request
    u.lang = user_data.lang
    u.listed_count = user_data.listed_count
    u.location = user_data.location
    u.name = user_data.name
    #u.needs_phone_verification = user_data.needs_phone_verification
    #u.profile_background_color = user_data.profile_background_color
    #u.profile_background_image_url = user_data.profile_background_image_url
    #u.profile_background_image_url_https = user_data.profile_background_image_url_https
    #u.profile_background_tile = user_data.profile_background_tile
    #u.profile_image_url = user_data.profile_image_url
    #u.profile_image_url_https = user_data.profile_image_url_https
    #u.profile_link_color = user_data.profile_link_color
    #u.profile_location = user_data.profile_location
    #u.profile_sidebar_border_color = user_data.profile_sidebar_border_color
    #u.profile_sidebar_fill_color = user_data.profile_sidebar_fill_color
    #u.profile_text_color = user_data.profile_text_color
    #u.profile_use_background_image = user_data.profile_use_background_image
    u.protected = user_data.protected
    u.screen_name = user_data.screen_name
    u.statuses_count = user_data.statuses_count
    # u.suspended = user_data.suspended
    u.time_zone = user_data.time_zone
    u.translator_type = user_data.translator_type
    u.url = user_data.url
    u.user_id = int(user_data.id_str)
    u.utc_offset = user_data.utc_offset
    u.verified = user_data.verified

    u.user_class = user_class
    u.data_source = data_source
    u.save()

    # Add relationship data if the user_class is 2 or higher
    if user_class >= 2:
        # Get users followed by account & create relationship objects
        user_following = userdata.friends_ids(screen_name=user_data.screen_name)
        for target_user in user_following:
            create_relo(u, target_user, outgoing=True)

        # Get followers & create relationship objects
        user_followers = userdata.followers_ids(screen_name=user_data.screen_name)
        for source_user in user_followers:
            create_relo(u, source_user, outgoing=False)
    return u


#TODO: Have commented out the updates to the in/out degree rows (to reduce db calls). Decide whether to remove.
def create_relo(existing_user, new_user_id, outgoing):

    if outgoing:
        if Relo.objects.filter(source_user=existing_user).filter(target_user__user_id=new_user_id).filter(end_observed_at=None).exists():
            return
    else: # Incoming relationship
        if Relo.objects.filter(source_user__user_id=new_user_id).filter(target_user=existing_user).filter(end_observed_at=None).exists():
            return

    r = Relo()
    r.observed_at = timezone.now()

    if outgoing:
        #existing_user.out_degree += 1
        #existing_user.save()
        r.source_user = existing_user

        # Create new users for targets if not already in DB
        try:
            tuser = User.objects.get(user_id=new_user_id)
        except:
            tuser = User()
            tuser.added_at = timezone.now()
            tuser.user_id = new_user_id
            tuser.user_class=0
        tuser.in_degree += 1
        tuser.save()
        r.target_user = tuser

    else: # Incoming relationship
            #existing_user.in_degree += 1
            #existing_user.save()
            r.target_user = existing_user

            # Create new users for targets if not already in DB
            try:
                suser = User.objects.get(user_id=new_user_id)
            except:
                suser = User()
                suser.added_at = timezone.now()
                suser.user_id = new_user_id
                suser.user_class=0
            suser.out_degree += 1
            suser.save()
            r.source_user = suser

    r.save()
    return


def save_user_timelines(users):
    try:
        event = Event.objects.all()[0]
    except:
        return
    start_time = event.time_start
    end_time = event.time_end
    user_count = users.count()
    progress_count = 0

    for user in users:
        print('Saving timeline for user: {}'.format(user.screen_name))

        timeline_old_enough = False # received timeline encompasses start_time
        max_id = False

        if progress_count % 10 == 0:
            print('Progress: {} of {}'.format(progress_count, user_count))
        progress_count += 1

        while timeline_old_enough is False:

            if max_id is False:
                statuses = userdata.user_timeline(id=user.user_id)
            else:
                statuses = userdata.user_timeline(id=user.user_id, max_id=max_id)

            if statuses is False:
                print('Timeline error with user: {}'.format(user.screen_name))
                timeline_old_enough = True
                break

            #Save to DB here
            for status in statuses:
                if int(status.id_str) < max_id or max_id is False:
                    max_id = int(status.id_str)
                tz_aware = timezone.make_aware(status.created_at, timezone=pytz.utc)

                if tz_aware > start_time:
                    if tz_aware < end_time:
                        try:
                            if status.truncated:
                                text=status.extended_tweet.get('full_text')
                            else:
                                try:
                                    text=status.text # TODO: Swap with full_text in exception?
                                except:
                                    text=status.full_text #TODO: Should try full_text before text?
                            save_tweet(status, data_source=0)
                        except:
                            pass
                    else:
                        #print('Tweet too new.')
                        max_id = int(status.id_str)
                else:
                    #print('Tweet too old.')
                    timeline_old_enough = True
            if len(statuses) < 200:
                timeline_old_enough = True
    return


def save_tweet(tweet_data, data_source, user_class=0, save_entities=False):
    tweet = Tweet()
    # If timezone is an issue:
    tz_aware = timezone.make_aware(tweet_data.created_at, timezone.get_current_timezone())
    tweet.created_at = tz_aware
    tweet.favorite_count = tweet_data.favorite_count
    #tweet.filter_level = tweet_data.filter_level
    tweet.tweet_id = int(tweet_data.id_str)
    tweet.lang = tweet_data.lang # nullable
    #tweet.possibly_sensitive = tweet_data.possibly_sensitive # nullable
    tweet.retweet_count = tweet_data.retweet_count
    tweet.source = tweet_data.source
    tweet.data_source = data_source

    if tweet_data.truncated:
        tweet.text=tweet_data.extended_tweet.get('full_text')
    else:
        # Try block to handle current issue with REST calls and extended_tweet
        try:
            tweet.text=tweet_data.text
        except:
            tweet.text=tweet_data.full_text

    try:
        tweet.coordinates_lat = tweet_data.coordinates.get('coordinates')[1] # nullable
        tweet.coordinates_lon = tweet_data.coordinates.get('coordinates')[0] # nullable
        tweet.coordinates_type = tweet_data.coordinates.get('type') # nullable
    except:
        pass
    if tweet_data.in_reply_to_status_id_str:
        tweet.in_reply_to_status_id = int(tweet_data.in_reply_to_status_id_str) # nullable
    if tweet_data.in_reply_to_user_id_str:
        tweet.in_reply_to_user_id = int(tweet_data.in_reply_to_user_id_str) # nullable
    try:
        tweet.quoted_status_id = int(tweet_data.quoted_status_id_str) # Only appears when relevant
    except:
        pass
    author_id = int(tweet_data.user.id_str)
    try:
        tweet.author = User.objects.get(user_id=author_id)
    except ObjectDoesNotExist:
        print('Author not in database, adding as new user')
        #add_user(user_id=author_id, data_source=data_source)       # Old method - user data from API rather than using object attached to tweet
        user = add_user(user_data=tweet_data.user, data_source=data_source, user_class=user_class)
        if user:
            tweet.author = user
        else:
            print('ERROR: save_user returned False during save_tweet.') # Probably detected as spam user, shouldn't happen from streamed Tweets.
    if tweet_data.place is not None:
        print('Saving place data for tweet: {}'.format(tweet_data.id_str)) # TESTING
        tweet.place = save_place(tweet_data.place)
    tweet.save()

    if save_entities:
        tags = tweet_data.entities.get('hashtags')
        for tag in tags:
            save_hashtag(tag.get('text'), tweet)

        urls = tweet_data.entities.get('urls')
        for u in urls:
            # TODO: Test url cleanup, decide whether to exlude twitter urls (save elsewhere?)
            url = u.get('expanded_url')
            # Cleanup URL
            url = re.sub('(http://|https://|#.*|&.*)', '', url)
            # Exclude twitter URLs, which are added if media is attached - therefore
            # not relevant to the analysis, but look at capturing in tweet data?
            if url[0:11] != 'twitter.com':
                save_url(url, tweet)

        user_mentions = tweet_data.entities.get('user_mentions')
        for user in user_mentions:
            save_mention(user.get('screen_name'), tweet)
            # TODO: Implement something here to add these users based on authors class?
            pass
        # TODO: save other entities?: media, user_mentions, symbols, extended_entities
        # https://dev.twitter.com/overview/api/entities-in-twitter-objects
    return


def save_place(place):
    place, created = Place.objects.get_or_create(
        place_id = place.id,
        url = place.url,
        place_type = place.place_type,
        name = place.name,
        full_name = place.full_name,
        country_code = place.country_code,
        country = place.country,
        lat_1 = place.bounding_box.coordinates[0][0][0],
        lon_1 = place.bounding_box.coordinates[0][0][1],
        lat_2 = place.bounding_box.coordinates[0][1][0],
        lon_2 = place.bounding_box.coordinates[0][1][1],
        lat_3 = place.bounding_box.coordinates[0][2][0],
        lon_3 = place.bounding_box.coordinates[0][2][1],
        lat_4 = place.bounding_box.coordinates[0][3][0],
        lon_4 = place.bounding_box.coordinates[0][3][1]
        )
    print('Saving place: {}'.format(place.name))
    return place


def save_hashtag(hashtag_text, tweet_object):
    hashtag_text = hashtag_text.lower()
    hashtag, created = Hashtag.objects.get_or_create(hashtag=hashtag_text)
    if created:
        hashtag.save()      # TODO: Is this save necessary? Should be part of get_or_create
    hashtag.tweets.add(tweet_object)
    return


def save_url(url_text, tweet_object):
    url, created = Url.objects.get_or_create(url=url_text)
    if created:
        url.save()
    url.tweets.add(tweet_object)
    return


def save_mention(mention_text, tweet_object):
    mention_text = mention_text.lower()
    mention, created = Mention.objects.get_or_create(mention=mention_text)
    if created:
        mention.save()
    mention.tweets.add(tweet_object)
    return
