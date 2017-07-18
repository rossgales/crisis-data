# Required ego degree values for an alter account to be considered relevant
REQUIRED_IN_DEGREE = 3
REQUIRED_OUT_DEGREE = 3

# Thresholds for determining spam/celebrity/news accounts
FOLLOWERS_THRESHOLD = 5000
FRIENDS_THRESHOLD = 5000
STATUSES_THRESHOLD = 10000

# Threshold proportion for a hashtag to appear before it is added to tracked tags
TAG_OCCURENCE_THRESHOLD = 0.05
# Threshold proportion for a mentioned user to appear before it is added as user_class=2
MENTION_OCCURENCE_THRESHOLD = 0.02

# Seconds between each keyword stream reset to get fresh keyword list
STREAM_REFRESH_RATE = 600

# Parameters of bounding box if single point coordinates are provided
BOUNDING_BOX_WIDTH = 0.8
BOUNDING_BOX_HEIGHT = 0.5

# Excludes isolated nodes from network_data_API
EXCLUDE_ISOLATED_NODES = True
