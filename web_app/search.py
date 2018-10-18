from flask import Blueprint
from wtforms import Form, validators, StringField
from flask import request
from flask import render_template
import requests
from requests import get
import bs4
import pandas as pd
from time import sleep
from time import time
from random import randint
from IPython.core.display import clear_output
from warnings import warn
import os
from os.path import dirname
import csv
from collections import Counter
import re
import gender_guesser.detector as gender
import spacy
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from collections import OrderedDict
from operator import itemgetter
# import time

bp = Blueprint('search', __name__)


class ReusableForm(Form):
    product_keyword = StringField(u'Name:', [validators.required(), validators.length(max=20)])


top_products = []
common_customer_phrases = []
gender_breakdown = {}
top_features = []
positive_features = {}
negative_features = {}
positive_feature_review_comments = {}
negative_feature_review_comments = {}
review_summary_dict = {}


@bp.route('/', methods=['GET', 'POST'])
def search():
    form = ReusableForm(request.form)

    print(form.errors)

    if request.method == 'POST':
        product_keyword = request.form['product_keyword']
        keyword_search = product_keyword.replace(' ', '+')
        print(product_keyword)

        if product_keyword:
            global top_products
            top_products = get_top_product_asins(keyword_search)

            for product in top_products:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.92 Safari/537.36'}
                response = get(
                    'https://www.amazon.com/gp/product/' + product,
                    headers=headers)
                if response.status_code != 200:
                    # print("The product {} returns no Amazon page, skipping to next.".format(product))
                    continue
                else:
                    html = get_html_from_web(product)
                    review_page_count = get_review_summary_data_from_html(html)
                    get_reviews_from_html(product, review_page_count)

            combine_reviews_for_keyword(keyword_search, top_products)

            global review_summary_dict
            review_summary_dict = calculate_reviews_summary_data(keyword_search)

            global common_customer_phrases
            common_customer_phrases = product_classifier(keyword_search)

            global gender_breakdown
            gender_breakdown = gender_analyzer(keyword_search)

            # feature extraction

            returned_list = get_product_reviews_list(keyword_search)
            pre_processing(returned_list, keyword_search)
            parts_of_speech(keyword_search)

            global top_features
            top_features_list = extract_features(keyword_search)
            top_features = top_features_list

            # sentiment_by_feature(top_features_list, returned_list, keyword_search)

            global positive_features
            positive_features = get_positive_features(top_features_list, keyword_search)

            global negative_features
            negative_features = get_negative_features(top_features_list, keyword_search)

            global positive_feature_review_comments
            positive_feature_review_comments = positive_feature_remarks(positive_features, keyword_search)

            global negative_feature_review_comments
            negative_feature_review_comments = negative_feature_remarks(negative_features, keyword_search)

    return render_template('search.html', form=form, top_products=top_products,
                           common_customer_phrases=common_customer_phrases, gender_breakdown=gender_breakdown,
                           top_features=top_features, positive_features=positive_features,
                           negative_features=negative_features,
                           positive_feature_review_comments=positive_feature_review_comments,
                           negative_feature_review_comments=negative_feature_review_comments,
                           review_summary_dict=review_summary_dict)


# todo test
def get_top_product_asins(keyword_search):
    print()
    print("Getting top product ASINS...")
    print()

    url = 'https://www.amazon.com/s/?field-keywords=' + keyword_search

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.92 Safari/537.36'}

    response = requests.get(url, headers=headers)

    html = response.text

    soup = bs4.BeautifulSoup(html, 'html.parser')

    top_products = {}

    # todo: refactor below into loop

    sleep(randint(2, 5))

    product_0 = soup.find('li', id="result_0")
    product_0_asin = product_0.attrs['data-asin']
    product_0_class = product_0.attrs['class']
    top_products.update({product_0_asin: product_0_class})

    sleep(randint(2, 5))

    product_1 = soup.find('li', id="result_1")
    product_1_asin = product_1.attrs['data-asin']
    product_1_class = product_1.attrs['class']
    top_products.update({product_1_asin: product_1_class})

    sleep(randint(2, 5))

    product_2 = soup.find('li', id="result_2")
    product_2_asin = product_2.attrs['data-asin']
    product_2_class = product_2.attrs['class']
    top_products.update({product_2_asin: product_2_class})

    sleep(randint(2, 5))

    product_3 = soup.find('li', id="result_3")
    product_3_asin = product_3.attrs['data-asin']
    product_3_class = product_3.attrs['class']
    top_products.update({product_3_asin: product_3_class})

    sleep(randint(2, 5))

    product_4 = soup.find('li', id="result_4")
    product_4_asin = product_4.attrs['data-asin']
    product_4_class = product_4.attrs['class']
    top_products.update({product_4_asin: product_4_class})

    sleep(randint(2, 5))

    product_5 = soup.find('li', id="result_5")
    product_5_asin = product_5.attrs['data-asin']
    product_5_class = product_5.attrs['class']
    top_products.update({product_5_asin: product_5_class})

    sleep(randint(2, 5))

    product_6 = soup.find('li', id="result_6")
    product_6_asin = product_6.attrs['data-asin']
    product_6_class = product_6.attrs['class']
    top_products.update({product_6_asin: product_6_class})

    sleep(randint(2, 5))

    product_7 = soup.find('li', id="result_7")
    product_7_asin = product_7.attrs['data-asin']
    product_7_class = product_7.attrs['class']
    top_products.update({product_7_asin: product_7_class})

    # Create list of ASINS not used for ads

    organic_results = []

    for product, value in top_products.items():
        if 'AdHolder' in value:
            continue
        else:
            organic_results.append(product)

    return organic_results


def get_html_from_web(asin):
    print()
    print("Getting HTML from product reviews page for {}.".format(asin))
    print()
    page_number = 1
    url = 'https://www.amazon.com/product-reviews/{}/ref=cm_cr_getr_d_paging_btm_{}?pageNumber={}'.format(asin,
                                                                                                          page_number,
                                                                                                          page_number)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.92 Safari/537.36'}
    response = requests.get(url, headers=headers)
    print('\n' + 'PRODUCT TO SCRAPE:'.format(page_number) + '\n')
    print(f"Product: {asin}")

    return response.text


def get_review_summary_data_from_html(html):
    soup = bs4.BeautifulSoup(html, 'html.parser')

    num_reviews = soup.find('span', attrs={'data-hook': 'total-review-count'}).get_text()
    num_reviews = re.sub('[!@#$.,\'\"]', '', num_reviews)

    review_pages = round((int(num_reviews) / 10) - 1)

    return review_pages


def get_reviews_from_html(asin, review_pages):
    print()
    print("Getting reviews for {}...".format(asin))
    print()

    # todo: remove duplicate ('headers' also in another function)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.92 Safari/537.36'}

    # Establish page numbers to scrape
    # todo: update to allow to scrape max number of pages using review_pages variable
    if review_pages == 1:
        pages = [str(i) for i in range(1, 1)]
    elif review_pages <= 10:
        # pages = [str(i) for i in range(1, review_pages)]
        pages = [str(i) for i in range(1, 4)]
    elif review_pages > 10:
        pages = [str(i) for i in range(1, 4)]
    print("Getting {} pages of reviews.".format(pages[-1]))
    print()

    # Lists to store the scraped data in
    review_ratings = []
    review_titles = []
    review_dates = []
    reviewer_names = []
    review_texts = []

    # Preparing the monitoring of the loop
    start_time = time()
    requests = 0

    # For every page in the interval 1-2
    for page in pages:
        # Make a get request
        response = get(
            'https://www.amazon.com/product-reviews/' + asin + '/ref=cm_cr_getr_d_paging_btm_' + page + '?pageNumber=' + page,
            headers=headers)
        sleep(randint(8, 15))

        # Monitor the requests
        requests += 1
        elapsed_time = time() - start_time
        print('Request: {}; Frequency: {} requests/s'.format(requests, requests / elapsed_time))
        print('Getting page {} of reviews...'.format(requests))
        clear_output(wait=True)

        # Throw a warning for non-200 status codes
        if response.status_code != 200:
            warn('Request: {}; Status code: {}'.format(requests, response.status_code))

        # Break the loop if the number of requests is greater than expected
        # todo: update to max number of reviews
        # todo: figure out if this is actually affecting anything (still allows to scrape more reviews)
        if requests > 100:
            warn('Number of requests was greater than expected.')
            break

        # Parse the content of the request with BeautifulSoup
        soup = bs4.BeautifulSoup(response.text, 'html.parser')

        # Select all the 10 reviews from a single page
        review_containers = soup.find_all('div', class_='a-section review')

        # For every review of these 10
        for container in review_containers:
            # Scrape the review rating
            first_review_rating = container.find('i', attrs={'data-hook': 'review-star-rating'}).get_text()
            review_ratings.append(first_review_rating)

            # Scrape the review title
            first_review_title = container.find('a', attrs={'data-hook': 'review-title'}).get_text()
            review_titles.append(first_review_title)

            # Scrape the review date
            first_review_date = container.find('span', attrs={'data-hook': 'review-date'}).get_text()
            review_dates.append(first_review_date)

            # Scrape the reviewer name
            first_review_reviewer_name = container.find('a', attrs={'data-hook': 'review-author'}).get_text()
            reviewer_names.append(first_review_reviewer_name)

            # Scrape the review text
            first_review_text = container.find('span', attrs={'data-hook': 'review-body'}).get_text()
            review_texts.append(first_review_text)

    product_reviews = pd.DataFrame({'review rating': review_ratings,
                                    'review title': review_titles,
                                    'review date': review_titles,
                                    'reviewer name': reviewer_names,
                                    'review text': review_texts})

    # Export reviews to csv file
    print()
    print("Exporting reviews to csv file...")
    print()

    base_folder = os.path.dirname(dirname(__file__))
    file_path = os.path.join(base_folder, 'data/product/product_reviews_' + asin + '.csv')

    product_reviews.to_csv(file_path)

    # Store review data in DB

    # get_reviews_from_html.first_review_reviewer_name = first_review_reviewer_name
    # get_reviews_from_html.first_review_text = first_review_text

    print("Product reviews export complete: {}".format(file_path))


def combine_reviews_for_keyword(keyword_search, top_products):
    print()
    print("Combining csv files for *{}* search phrase...".format(keyword_search))
    print()

    url = 'https://www.amazon.com/s/?field-keywords=' + keyword_search

    # print(url)
    # print(top_products)

    base_folder = os.path.dirname(dirname(__file__))
    file_path = os.path.join(base_folder, 'data/search_keyword/product_reviews_' + keyword_search + '.csv')

    combined_csv = open(file_path, 'w')

    csv_list = []

    for product in top_products:
        # csv_list.append('../data/product/product_reviews_' + product + '.csv')
        csv_list.append(os.path.join(base_folder, 'data/product/product_reviews_' + product + '.csv'))

    # print(csv_list)

    for file in csv_list:
        if os.path.isfile(file):
            csv_in = open(file)
            # print("{} file opened.".format(file))
            next(csv_in)
            for line in csv_in:
                combined_csv.write(line)
            # csv_in.close()
            # combined_csv.close()
        else:
            continue


def calculate_reviews_summary_data(keyword_search):
    print()
    print("Calculating reviews summary data...")
    print()

    base_folder = os.path.dirname(dirname(__file__))
    file_path = os.path.join(base_folder, 'data/search_keyword/product_reviews_' + keyword_search + '.csv')

    f = open(file_path)
    csv_f = csv.reader(f)

    review_rating_total = 0

    # count number of reviews
    num_reviews_total = 0
    for row in csv_f:
        num_reviews_total += 1
        rating = re.sub(' out of 5 stars', '', row[1])
        rating = float(rating)
        review_rating_total += rating

    average_review_rating = review_rating_total / num_reviews_total

    print("The total number of reviews is {}.".format(num_reviews_total))
    print("The average review rating is {}.".format(average_review_rating))

    review_summary_dict = {'Total Reviews': num_reviews_total, 'Average Review Rating': average_review_rating}

    print(review_summary_dict)

    return review_summary_dict


def product_classifier(keyword_search):
    print()
    print("Classifying this product...")
    print()

    # Import csv file with scraped product reviews

    base_folder = os.path.dirname(dirname(__file__))
    file_path = os.path.join(base_folder, 'data/search_keyword/product_reviews_' + keyword_search + '.csv')

    f = open(file_path)
    csv_f = csv.reader(f)

    # create string of product reviews
    product_reviews = []

    for row in csv_f:
        product_reviews.append(row[5])

    product_reviews_list = str(product_reviews).strip('[]')
    product_reviews_list = product_reviews_list.lower()

    # Use reviews to determine what a product is (classify it) to customers
    product_mentions = []

    for m in re.finditer('this ', product_reviews_list):
        next_word_end = product_reviews_list.find(' ', m.end())
        next_word = product_reviews_list[m.end():next_word_end].strip()
        next_word = re.sub('[!@#$.,\'\"]', '', next_word)
        period_end_lookup = product_reviews_list[next_word_end - 1]
        if period_end_lookup != '.':
            next_next_word_end = product_reviews_list.find(' ', next_word_end + 1)
            next_next_word = product_reviews_list[next_word_end + 1:next_next_word_end].strip()
            next_next_word = re.sub('[!@#$.,\'\"]', '', next_next_word)
            product_mentions.append(next_word)
            product_mentions.append(next_word + ' ' + next_next_word)
        else:
            product_mentions.append(next_word)

    # todo: add all stop words
    cnt = Counter()
    for word in product_mentions:
        if word == "is" or word == "product" or word == "one" or word == "I" or word == "It" or word == "You" or word == "We" or word == "It\\\\s" or word == "He" or word == "thing":
            continue
        else:
            cnt[word] += 1

    top_product_names = dict(cnt.most_common(3))

    print("This product is most commonly referred to by customers as...")
    print(top_product_names)
    print()

    return top_product_names


def gender_analyzer(keyword_search):
    print()
    print("Analyzing gender of reviewers...")
    print()

    base_folder = os.path.dirname(dirname(__file__))
    file_path = os.path.join(base_folder, 'data/search_keyword/product_reviews_' + keyword_search + '.csv')

    f = open(file_path)
    csv_f = csv.reader(f)

    reviewer_gender_list = []

    for row in csv_f:
        names = row[4].split()
        d = gender.Detector()
        reviewer_gender = d.get_gender(names[0])
        reviewer_gender_list.append(reviewer_gender)

    male_count = reviewer_gender_list.count('male') + reviewer_gender_list.count('mostly_male')
    female_count = reviewer_gender_list.count('female') + reviewer_gender_list.count('mostly_female')

    male_percentage = male_count / (male_count + female_count)
    female_percentage = female_count / (male_count + female_count)

    # gender_dict = {'Male': male_percentage, 'Female': female_percentage}
    gender_dict = {'Male': '{0:.1f}'.format(male_percentage * 100), 'Female': '{0:.1f}'.format(female_percentage * 100)}

    print("Male: {} or {:.1%}".format(male_count, male_percentage))
    print("Female: {} or {:.1%}".format(female_count, female_percentage))
    print("Unknown: {}".format(reviewer_gender_list.count('unknown')))
    print()

    return gender_dict


def get_product_reviews_list(keyword_search):
    base_folder = os.path.dirname(dirname(__file__))
    file_path = os.path.join(base_folder, 'data/search_keyword/product_reviews_' + keyword_search + '.csv')

    f = open(file_path)
    csv_f = csv.reader(f)

    # create string of product reviews

    product_reviews_list = []

    first_line = True

    for row in csv_f:
        if first_line:
            first_line = False
            continue
        product_reviews_list.append(row[5] + ' ')

    product_reviews = str(product_reviews_list).strip('[]')

    product_reviews = re.sub('[(){}<>\']', '', product_reviews)

    return product_reviews


def pre_processing(reviews, keyword_search):
    print()
    # Remove stop words

    stop_words = set(stopwords.words('english'))

    word_tokens = word_tokenize(reviews)

    filtered_reviews = [w for w in word_tokens if not w in stop_words]

    filtered_reviews = []

    for w in word_tokens:
        if w not in stop_words:
            filtered_reviews.append(w)

    reviews_string = str(filtered_reviews).strip('[]')

    reviews_string = re.sub('[(){}`<>\",\']', '', reviews_string)

    # Break into sentences

    nlp = spacy.load('en_core_web_sm')
    doc = nlp(reviews_string)

    base_folder = os.path.dirname(dirname(__file__))
    file_path = os.path.join(base_folder, 'data/search_keyword/product_reviews_sentences_' + keyword_search + '.csv')

    with open(file_path, 'w') as newFile:
        new_file_writer = csv.writer(newFile)
        print("Adding sentences to new csv file...")
        # todo: figure out way to skip sentences with only 1-2 words in them
        for sent in doc.sents:
            new_file_writer.writerow([sent])
    print()
    print("New csv with sentences ready.")
    print()


def parts_of_speech(keyword_search):
    # Tag parts of speech for each sentence

    nlp = spacy.load('en_core_web_sm')

    base_folder = os.path.dirname(dirname(__file__))

    input_file = open(
        os.path.join(base_folder, 'data/search_keyword/product_reviews_sentences_' + keyword_search + '.csv'), 'r')

    output_file = open(os.path.join(base_folder, 'data/search_keyword/product_reviews_POS_' + keyword_search + '.csv'),
                       'w')

    for row in input_file:
        row_to_pos = nlp(row)
        new_line = []
        for token in row_to_pos:
            new_line.append('(' + "'" + token.text + "'" + ', ' + "'" + token.tag_ + "'" + ')')
        sentence_string = str(new_line)
        sentence_string = sentence_string.replace("\"(", "(")
        sentence_string = sentence_string.replace("\')\",", "\'),")
        output_file.write(sentence_string + '\n')
    print("CSV ready with part of speech.")


def extract_features(keyword_search):
    print()
    print("Extracting features...")
    print()

    base_folder = os.path.dirname(dirname(__file__))
    file_path = os.path.join(base_folder, 'data/search_keyword/product_reviews_sentences_' + keyword_search + '.csv')

    input_file = open(file_path, 'r')

    nlp = spacy.load('en_core_web_sm')

    feature_list = []

    for row in input_file:
        row_to_pos = nlp(row)
        for chunk in row_to_pos.noun_chunks:
            feature_list.append(chunk.root.text)

    cnt = Counter()
    for word in feature_list:
        if word == "I" or word == "people" or word == "product" or word == "It" or word == "You" or word == "We" or word == "It\\\\s" or word == "He" or word == "thing":
            continue
        else:
            cnt[word] += 1

    top_features = dict(cnt.most_common(10))

    # print(top_features)

    return top_features


def sentiment_by_feature(features, reviews, keyword_search):
    top_features_list = list(features.keys())

    base_folder = os.path.dirname(dirname(__file__))
    file_path = os.path.join(base_folder, 'data/search_keyword/product_reviews_' + keyword_search + '.csv')

    f = open(file_path)
    csv_f = csv.reader(f)

    positive_reviews = []
    negative_reviews = []

    for row in csv_f:
        # print(row[1])
        if row[1] == '3.0 out of 5 stars':
            continue
        if row[1] == '1.0 out of 5 stars' or row[1] == '2.0 out of 5 stars':
            negative_reviews.append(row[5])
        if row[1] == '4.0 out of 5 stars' or row[1] == '5.0 out of 5 stars':
            positive_reviews.append(row[5])

    negative_weighted_average = len(positive_reviews) / len(negative_reviews)

    positive_reviews_string = str(positive_reviews)
    negative_reviews_string = str(negative_reviews)

    positive_review_features = {}
    negative_review_features = {}

    for feature in top_features_list:
        positive_mentions = positive_reviews_string.count(feature)
        negative_mentions = negative_reviews_string.count(feature)
        positive_review_features.update({feature: positive_mentions})
        negative_review_features.update({feature: round(negative_mentions * negative_weighted_average)})

    positive_features_sorted = OrderedDict(sorted(positive_review_features.items(), key=itemgetter(1), reverse=True))
    negative_features_sorted = OrderedDict(sorted(negative_review_features.items(), key=itemgetter(1), reverse=True))

    print("Features most common in positive reviews: ", positive_features_sorted)
    print()
    print("Features most common in negative reviews: ", negative_features_sorted)
    print()

    nlp = spacy.load('en_core_web_sm')
    doc = nlp(positive_reviews_string)

    with open(os.path.join(base_folder, 'data/search_keyword/positive_reviews_sentences_' + keyword_search + '.csv'),
              'w') as newFile:
        # with open('data/search_keyword/positive_reviews_sentences_' + keyword_search + '.csv', 'w') as newFile:
        new_file_writer = csv.writer(newFile)
        print("Adding positive review sentences to new csv file...")
        print()
        for sent in doc.sents:
            new_file_writer.writerow([sent])

    doc = nlp(negative_reviews_string)

    with open(os.path.join(base_folder, 'data/search_keyword/negative_reviews_sentences_' + keyword_search + '.csv'),
              'w') as newFile:
        # with open('data/search_keyword/negative_reviews_sentences_' + keyword_search + '.csv', 'w') as newFile:
        new_file_writer = csv.writer(newFile)
        print("Adding negative review sentences to new csv file...")
        for sent in doc.sents:
            new_file_writer.writerow([sent])

    # Check reviewer comments for top positive feature

    file_path = os.path.join(base_folder, 'data/search_keyword/positive_reviews_sentences_' + keyword_search + '.csv')

    f = open(file_path)
    csv_f = csv.reader(f)

    feature_to_check = list(positive_features_sorted.keys())[0]

    print()
    print("SAMPLE - A few positive comments from reviewers about most common feature * {} *: ".format(feature_to_check))

    positive_feature_comments = []

    for row in csv_f:
        if any(feature_to_check in s for s in row):
            # print(row)
            positive_feature_comments.append(row)
        else:
            continue

    print(positive_feature_comments[:4])
    print()

    # Check reviewer comments for top negative feature

    file_path = os.path.join(base_folder, 'data/search_keyword/negative_reviews_sentences_' + keyword_search + '.csv')

    f = open(file_path)
    csv_f = csv.reader(f)

    negative_feature_to_check = list(negative_features_sorted.keys())[1]

    print("SAMPLE - A few negative comments from reviewers about most common feature * {} *: ".format(
        negative_feature_to_check))

    negative_feature_comments = []

    for row in csv_f:
        if any(negative_feature_to_check in s for s in row):
            # print(row)
            negative_feature_comments.append(row)
        else:
            continue

    print(negative_feature_comments[:4])


def get_positive_features(features, keyword_search):
    top_features_list = list(features.keys())

    base_folder = os.path.dirname(dirname(__file__))
    file_path = os.path.join(base_folder, 'data/search_keyword/product_reviews_' + keyword_search + '.csv')

    f = open(file_path)
    csv_f = csv.reader(f)

    positive_reviews = []
    negative_reviews = []

    for row in csv_f:
        # print(row[1])
        if row[1] == '3.0 out of 5 stars':
            continue
        if row[1] == '1.0 out of 5 stars' or row[1] == '2.0 out of 5 stars':
            negative_reviews.append(row[5])
        if row[1] == '4.0 out of 5 stars' or row[1] == '5.0 out of 5 stars':
            positive_reviews.append(row[5])

    # negative_weighted_average = len(positive_reviews) / len(negative_reviews)

    positive_reviews_string = str(positive_reviews)
    # negative_reviews_string = str(negative_reviews)

    positive_review_features = {}
    # negative_review_features = {}

    for feature in top_features_list:
        positive_mentions = positive_reviews_string.count(feature)
        # negative_mentions = negative_reviews_string.count(feature)
        positive_review_features.update({feature: positive_mentions})
        # negative_review_features.update({feature: round(negative_mentions * negative_weighted_average)})

    positive_features_sorted = OrderedDict(sorted(positive_review_features.items(), key=itemgetter(1), reverse=True))
    # negative_features_sorted = OrderedDict(sorted(negative_review_features.items(), key=itemgetter(1), reverse=True))

    print("Features most common in positive reviews: ", positive_features_sorted)
    print()
    # print("Features most common in negative reviews: ", negative_features_sorted)
    # print()

    return positive_features_sorted


def get_negative_features(features, keyword_search):
    top_features_list = list(features.keys())

    base_folder = os.path.dirname(dirname(__file__))
    file_path = os.path.join(base_folder, 'data/search_keyword/product_reviews_' + keyword_search + '.csv')

    f = open(file_path)
    csv_f = csv.reader(f)

    positive_reviews = []
    negative_reviews = []

    for row in csv_f:
        # print(row[1])
        if row[1] == '3.0 out of 5 stars':
            continue
        if row[1] == '1.0 out of 5 stars' or row[1] == '2.0 out of 5 stars':
            negative_reviews.append(row[5])
        if row[1] == '4.0 out of 5 stars' or row[1] == '5.0 out of 5 stars':
            positive_reviews.append(row[5])

    negative_weighted_average = len(positive_reviews) / len(negative_reviews)

    # positive_reviews_string = str(positive_reviews)
    negative_reviews_string = str(negative_reviews)

    # positive_review_features = {}
    negative_review_features = {}

    for feature in top_features_list:
        # positive_mentions = positive_reviews_string.count(feature)
        negative_mentions = negative_reviews_string.count(feature)
        # positive_review_features.update({feature: positive_mentions})
        negative_review_features.update({feature: round(negative_mentions * negative_weighted_average)})

    # positive_features_sorted = OrderedDict(sorted(positive_review_features.items(), key=itemgetter(1), reverse=True))
    negative_features_sorted = OrderedDict(sorted(negative_review_features.items(), key=itemgetter(1), reverse=True))

    # print("Features most common in positive reviews: ", positive_features_sorted)
    # print()
    print("Features most common in negative reviews: ", negative_features_sorted)
    print()

    return negative_features_sorted


def positive_feature_remarks(positive_features, keyword_search):
    base_folder = os.path.dirname(dirname(__file__))
    file_path = os.path.join(base_folder, 'data/search_keyword/product_reviews_' + keyword_search + '.csv')

    f = open(file_path)
    csv_f = csv.reader(f)

    positive_reviews = []
    negative_reviews = []

    for row in csv_f:
        # print(row[1])
        if row[1] == '3.0 out of 5 stars':
            continue
        if row[1] == '1.0 out of 5 stars' or row[1] == '2.0 out of 5 stars':
            negative_reviews.append(row[5])
        if row[1] == '4.0 out of 5 stars' or row[1] == '5.0 out of 5 stars':
            positive_reviews.append(row[5])

    # negative_weighted_average = len(positive_reviews) / len(negative_reviews)

    positive_reviews_string = str(positive_reviews)

    nlp = spacy.load('en_core_web_sm')
    doc = nlp(positive_reviews_string)

    with open(os.path.join(base_folder, 'data/search_keyword/positive_reviews_sentences_' + keyword_search + '.csv'),
              'w') as newFile:
        new_file_writer = csv.writer(newFile)
        print()
        for sent in doc.sents:
            # print(sent)
            new_file_writer.writerow([sent])

    # Check reviewer comments for top positive feature

    file_path = os.path.join(base_folder, 'data/search_keyword/positive_reviews_sentences_' + keyword_search + '.csv')

    f = open(file_path)
    csv_f = csv.reader(f)

    # for row in csv_f:
    #     row = str(row)
    #     row = row.replace("['", "")
    #     row = row.replace("']", "")
    #     row = row.replace("\"]", "")
    #     row = row.replace("[\"", "")
    #     row = row.replace("\\'", "'")
    #     row = row.replace("\'", "'")
    #     row = row.strip()

    positive_feature_dict = {}

    positive_features_list = []

    for key in positive_features.keys():
        positive_features_list.append(key)

    comment_list_0 = []
    comment_list_1 = []
    comment_list_2 = []
    comment_list_3 = []
    comment_list_4 = []
    comment_list_5 = []
    comment_list_6 = []
    comment_list_7 = []
    comment_list_8 = []
    comment_list_9 = []

    for row in csv_f:
        if any(positive_features_list[0] in s for s in row):
            comment_list_0.append(row)
        if any(positive_features_list[1] in s for s in row):
            comment_list_1.append(row)
        if any(positive_features_list[2] in s for s in row):
            comment_list_2.append(row)
        if any(positive_features_list[3] in s for s in row):
            comment_list_3.append(row)
        if any(positive_features_list[4] in s for s in row):
            comment_list_4.append(row)
        if any(positive_features_list[5] in s for s in row):
            comment_list_5.append(row)
        if any(positive_features_list[6] in s for s in row):
            comment_list_6.append(row)
        if any(positive_features_list[7] in s for s in row):
            comment_list_7.append(row)
        if any(positive_features_list[8] in s for s in row):
            comment_list_8.append(row)
        if any(positive_features_list[9] in s for s in row):
            comment_list_9.append(row)

    positive_feature_dict.update({positive_features_list[0]: comment_list_0[:5]})
    positive_feature_dict.update({positive_features_list[1]: comment_list_1[:5]})
    positive_feature_dict.update({positive_features_list[2]: comment_list_2[:5]})
    positive_feature_dict.update({positive_features_list[3]: comment_list_3[:5]})
    positive_feature_dict.update({positive_features_list[4]: comment_list_4[:5]})
    positive_feature_dict.update({positive_features_list[5]: comment_list_5[:5]})
    positive_feature_dict.update({positive_features_list[6]: comment_list_6[:5]})
    positive_feature_dict.update({positive_features_list[7]: comment_list_7[:5]})
    positive_feature_dict.update({positive_features_list[8]: comment_list_8[:5]})
    positive_feature_dict.update({positive_features_list[9]: comment_list_9[:5]})

    for key, value in positive_feature_dict.items():
        print(key)
        for elem in value:
            # elem = re.sub("['", '', elem)
            # elem = re.sub("']", '', elem)
            print('> {}'.format(elem))
        print()

    return positive_feature_dict


def negative_feature_remarks(negative_features, keyword_search):
    base_folder = os.path.dirname(dirname(__file__))
    file_path = os.path.join(base_folder, 'data/search_keyword/product_reviews_' + keyword_search + '.csv')

    f = open(file_path)
    csv_f = csv.reader(f)

    positive_reviews = []
    negative_reviews = []

    for row in csv_f:
        # print(row[1])
        if row[1] == '3.0 out of 5 stars':
            continue
        if row[1] == '1.0 out of 5 stars' or row[1] == '2.0 out of 5 stars':
            negative_reviews.append(row[5])
        if row[1] == '4.0 out of 5 stars' or row[1] == '5.0 out of 5 stars':
            positive_reviews.append(row[5])

    # negative_weighted_average = len(positive_reviews) / len(negative_reviews)

    # positive_reviews_string = str(positive_reviews)
    negative_reviews_string = str(negative_reviews)

    nlp = spacy.load('en_core_web_sm')
    doc = nlp(negative_reviews_string)

    with open(os.path.join(base_folder, 'data/search_keyword/negative_reviews_sentences_' + keyword_search + '.csv'),
              'w') as newFile:
        new_file_writer = csv.writer(newFile)
        print()
        for sent in doc.sents:
            new_file_writer.writerow([sent])

    # Check reviewer comments for top positive feature

    file_path = os.path.join(base_folder, 'data/search_keyword/negative_reviews_sentences_' + keyword_search + '.csv')

    f = open(file_path)
    csv_f = csv.reader(f)

    # for row in csv_f:
    #     row = str(row)
    #     row = row.replace("['", "")
    #     row = row.replace("']", "")
    #     row = row.replace("\"]", "")
    #     row = row.replace("[\"", "")
    #     row = row.replace("\\'", "'")
    #     row = row.replace("\'", "'")

    negative_feature_dict = {}

    negative_features_list = []

    for key in negative_features.keys():
        negative_features_list.append(key)

    comment_list_0 = []
    comment_list_1 = []
    comment_list_2 = []
    comment_list_3 = []
    comment_list_4 = []
    comment_list_5 = []
    comment_list_6 = []
    comment_list_7 = []
    comment_list_8 = []
    comment_list_9 = []

    for row in csv_f:
        if any(negative_features_list[0] in s for s in row):
            comment_list_0.append(row)
        if any(negative_features_list[1] in s for s in row):
            comment_list_1.append(row)
        if any(negative_features_list[2] in s for s in row):
            comment_list_2.append(row)
        if any(negative_features_list[3] in s for s in row):
            comment_list_3.append(row)
        if any(negative_features_list[4] in s for s in row):
            comment_list_4.append(row)
        if any(negative_features_list[5] in s for s in row):
            comment_list_5.append(row)
        if any(negative_features_list[6] in s for s in row):
            comment_list_6.append(row)
        if any(negative_features_list[7] in s for s in row):
            comment_list_7.append(row)
        if any(negative_features_list[8] in s for s in row):
            comment_list_8.append(row)
        if any(negative_features_list[9] in s for s in row):
            comment_list_9.append(row)

    negative_feature_dict.update({negative_features_list[0]: comment_list_0[:5]})
    negative_feature_dict.update({negative_features_list[1]: comment_list_1[:5]})
    negative_feature_dict.update({negative_features_list[2]: comment_list_2[:5]})
    negative_feature_dict.update({negative_features_list[3]: comment_list_3[:5]})
    negative_feature_dict.update({negative_features_list[4]: comment_list_4[:5]})
    negative_feature_dict.update({negative_features_list[5]: comment_list_5[:5]})
    negative_feature_dict.update({negative_features_list[6]: comment_list_6[:5]})
    negative_feature_dict.update({negative_features_list[7]: comment_list_7[:5]})
    negative_feature_dict.update({negative_features_list[8]: comment_list_8[:5]})
    negative_feature_dict.update({negative_features_list[9]: comment_list_9[:5]})

    for key, value in negative_feature_dict.items():
        print(key)
        for elem in value:
            print('> {}'.format(elem))
        print()

    return negative_feature_dict
