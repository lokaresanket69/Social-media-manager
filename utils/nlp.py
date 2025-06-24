import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

nltk.download('punkt')
nltk.download('stopwords')

def generate_caption(description):
    tokens = word_tokenize(description.lower())
    stop_words = set(stopwords.words('english'))
    keywords = [word for word in tokens if word.isalpha() and word not in stop_words]
    hashtags = ['#' + word for word in keywords[:5]]
    return description + '\n\n' + ' '.join(hashtags)
