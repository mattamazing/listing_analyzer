from flask import Blueprint
from wtforms import Form, validators, StringField
from flask import request
from flask import render_template
import requests
from requests import get
import bs4
import requests
import re
from time import sleep
from random import randint
from PIL import Image
from io import BytesIO
from sightengine.client import SightengineClient
import dash
import os

app = dash.Dash(__name__)
server = app.server
server.secret_key = os.environ.get('secret_key', 'secret')

bp = Blueprint('search', __name__)

image_urls = []
product_title = ""
listing_score_details = {}


class ReusableForm(Form):
    product_keyword = StringField(u'Name:', [validators.required(), validators.length(max=20)])


@bp.route('/', methods=['GET', 'POST'])
def search():
    form = ReusableForm(request.form)

    print(form.errors)

    if request.method == 'POST':
        asin = request.form['asin']
        main_keyword = request.form['main_keyword']
        print(asin)
        print(main_keyword)

        html = get_html_from_asin(asin)
        global image_urls
        image_urls = scrape_image_urls(html)

        global product_title
        product_title = scrape_title(html)

        global product_bullets
        product_bullets = scrape_bullets(html)

        global product_description
        product_description = scrape_description(html)

        global top_review_ratings
        top_review_ratings = scrape_top_review_ratings(html)

        global recent_review_ratings
        recent_review_ratings = scrape_most_recent_review_ratings(html, asin)

        global image_count_actual
        image_count_actual = count_number_images(image_urls)

        image_resolution_dict = {}
        image_count = 1
        for image in image_urls:
            image_resolution = analyze_image_resolution(image)
            # print("Image {}: {}".format(image_count, image_resolution))
            image_resolution_dict.update({image_count: image_resolution})
            image_count += 1

        # todo: uncomment to use image properties function
        # print()
        # print("Image properties:")
        # image_properties = {}
        # image_count = 1
        #
        # for image in image_urls:
        #     properties = analyze_image_properties(image)
        #     image_properties[image] = properties
        #     print("Image {}: {}".format(image_count, properties))
        #     image_count += 1

        keyword_in_title = check_main_keyword_in_title(product_title, main_keyword)

        bullet_length = {}
        bullet_id = 1
        for bullet in product_bullets:
            bullet_len = check_bullet_length(bullet)
            bullet_length.update({bullet_id: bullet_len})
            bullet_id += 1

        description_length = check_description_length(product_description)
        # print()
        # print("Description length: {}".format(description_length))

        overall_review_rating = check_overall_review_rating(html)
        # print()
        # print("Overall review rating: {}".format(overall_review_rating))

        total_review_count = check_total_reviews(html)
        # print()
        # print("Total review count: {}".format(total_review_count))

        using_coupon_feature = check_using_coupon_feature(html)
        # print()
        # print("Using coupon feature: {}".format(using_coupon_feature))

        using_enhanced_brand_content = check_if_enhanced_brand_content(html)
        # print()
        # print("Using Enhanced Brand Content: {}".format(using_enhanced_brand_content))

        all_images_1000 = images_at_least_1000(image_resolution_dict)

        global listing_score_details
        listing_score_details = calculate_listing_score(image_count_actual, keyword_in_title, overall_review_rating,
                                                        description_length, top_review_ratings, recent_review_ratings,
                                                        bullet_length, using_coupon_feature,
                                                        using_enhanced_brand_content,
                                                        all_images_1000)

    return render_template('search.html', form=form, image_urls=image_urls, listing_score_details=listing_score_details,
                           product_title=product_title)


def get_html_from_asin(asin):
    url = 'https://www.amazon.com/dp/{}/'.format(asin)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.92 Safari/537.36'}
    response = requests.get(url, headers=headers)

    # html = bs4.BeautifulSoup(response.text, 'html.parser')
    html = bs4.BeautifulSoup(response.text, 'html5lib')

    return html


def scrape_image_urls(html):
    soup = html

    javascript_containers = soup.find_all('script', attrs={'type': 'text/javascript'})

    re1 = '("hiRes")'  # Double Quote String 1
    re2 = '.*?'  # Non-greedy match on filler
    re3 = '((?:http|https)(?::\\/{2}[\\w]+)(?:[\\/|\\.]?)(?:[^\\s"]*))'  # HTTP URL 1

    image_url_list = []

    for container in javascript_containers:
        txt = container.get_text()
        pattern = re.compile(re1 + re2 + re3, re.IGNORECASE | re.DOTALL)
        m = pattern.search(txt)
        if len(image_url_list) == 0:
            for (types, images) in re.findall(pattern, txt):
                image_url_list.append(images)
        else:
            break

    image_url_unique = list(set(image_url_list))

    return image_url_unique


def scrape_title(html):
    soup = html

    product_title = soup.find('span', attrs={'id': 'productTitle'}).get_text()

    product_title = product_title.strip()

    return product_title


def scrape_bullets(html):
    soup = html

    product_bullets = []

    bullets_container = soup.find('div', attrs={'id': 'feature-bullets'}).find_all('span',

                                                                                   attrs={'class': 'a-list-item'})

    for bullet in bullets_container:
        if 'Make sure this fits\nby entering your model number.' in bullet.get_text():
            continue
        else:
            bullet_text = bullet.get_text()
            product_bullets.append(bullet_text.strip())

    return product_bullets


def scrape_description(html):
    soup = html

    product_description = soup.find('div', attrs={'id': 'productDescription'}).get_text()

    product_description = product_description.strip()

    return product_description


def scrape_top_review_ratings(html):
    soup = html

    top_reviews_container = soup.find_all('div', class_='a-section review')

    top_reviews = {}

    review_position = 1

    for review in top_reviews_container:
        # sleep(randint(2, 5))
        position_name = 'Position {}'.format(review_position)
        try:
            review_rating = review.find('i', attrs={'data-hook': 'review-star-rating'}).get_text()
            review_rating = re.sub(' out of 5 stars', '', review_rating)
            if review_rating == "1.0":
                review_rating = 1
            elif review_rating == "2.0":
                review_rating = 2
            elif review_rating == "3.0":
                review_rating = 3
            elif review_rating == "4.0":
                review_rating = 4
            elif review_rating == "5.0":
                review_rating = 5
            top_reviews.update({position_name: review_rating})
            review_position += 1
        except AttributeError:
            # review_rating = "Scrape failed"
            continue

    return top_reviews


def scrape_most_recent_review_ratings(html, asin):
    soup = html

    recent_reviews_container = soup.find_all('i', attrs={'data-hook': 'review-star-rating-recent'})

    print()
    print("Recent reviews found in HTML: {}".format(len(recent_reviews_container)))

    recent_reviews = {}

    review_position = 1

    if len(recent_reviews_container) == 0:
        url = 'https://www.amazon.com/dp/{}/'.format(asin)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.92 Safari/537.36'}
        sleep(randint(5, 8))
        response = requests.get(url, headers=headers)
        soup = bs4.BeautifulSoup(response.text, 'html.parser')
        recent_reviews_container = soup.find_all('i', attrs={'data-hook': 'review-star-rating-recent'})

        print("Recent reviews found in fresh scrape of {}: {}".format(asin, len(recent_reviews_container)))

        for review in recent_reviews_container:
            position_name = 'Position {}'.format(review_position)
            sleep(randint(2, 5))
            try:
                review_rating = review.get_text()
                review_rating = re.sub(' out of 5 stars', '', review_rating)
                if review_rating == "1.0":
                    review_rating = 1
                elif review_rating == "2.0":
                    review_rating = 2
                elif review_rating == "3.0":
                    review_rating = 3
                elif review_rating == "4.0":
                    review_rating = 4
                elif review_rating == "5.0":
                    review_rating = 5
            except AttributeError:
                review_rating = "Scrape failed"
            recent_reviews.update({position_name: review_rating})
            review_position += 1
    else:
        for review in recent_reviews_container:
            position_name = 'Position {}'.format(review_position)
            # sleep(randint(2, 5))
            try:
                review_rating = review.get_text()
                review_rating = re.sub(' out of 5 stars', '', review_rating)
                if review_rating == "1.0":
                    review_rating = 1
                elif review_rating == "2.0":
                    review_rating = 2
                elif review_rating == "3.0":
                    review_rating = 3
                elif review_rating == "4.0":
                    review_rating = 4
                elif review_rating == "5.0":
                    review_rating = 5
            except AttributeError:
                review_rating = "Scrape failed"
            recent_reviews.update({position_name: review_rating})
            review_position += 1

    return recent_reviews


def count_number_images(image_urls):
    image_count = len(image_urls)

    return image_count


def analyze_image_resolution(image):
    # print("Measuring resolution for: {}".format(image))
    response = requests.get(image)
    current_image = Image.open(BytesIO(response.content))

    image_resolution = current_image.size
    # print(image_resolution)

    return image_resolution


def analyze_image_properties(image):
    """Analyze image with https://sightengine.com/demo - determines if image is a natural (real) photo, sharpness,
    and contrast."""

    # print("Analyzing image properties for {}".format(image))

    client = SightengineClient('1803656177', '3mDBzEtgy2YaUrWDhU4D')

    output_properties = client.check('properties').set_url(image)

    output_type = client.check('type').set_url(image)

    # image_properties = {}

    properties = {'Sharpness': output_properties['sharpness'], 'Brightness': output_properties['brightness'],
                  'Contrast': output_properties['contrast'],
                  'Image type': output_type['type']}

    # image_properties[image] = properties

    # print(image_properties)

    return properties


def check_main_keyword_in_title(product_title, main_keyword):
    keyword_in_title = main_keyword.lower() in product_title.lower()

    return keyword_in_title


def check_title_grammar():
    pass


def check_bullet_length(bullet):
    bullet_length = len(bullet)
    return bullet_length


def check_bullet_grammar():
    pass


def check_description_length(product_description):
    description_length = len(product_description)

    return description_length


def check_description_grammar():
    pass


def check_overall_review_rating(html):
    soup = html

    overall_review_rating = soup.find('span', attrs={'id': 'acrPopover'}).get_text()

    overall_review_rating = overall_review_rating.strip()

    overall_review_rating = re.sub(' out of 5 stars', '', overall_review_rating)

    overall_review_rating = float(overall_review_rating)

    return overall_review_rating


def check_total_reviews(html):
    soup = html

    total_review_count = soup.find('span', attrs={'id': 'acrCustomerReviewText'}).get_text()

    total_review_count = total_review_count.strip()

    total_review_count = re.sub(' customer reviews', '', total_review_count)

    return total_review_count


def check_using_coupon_feature(html):
    soup = html

    try:
        find_coupon_feature = soup.find('i', attrs={'class': 'a-icon a-icon-addon couponBadge'}).get_text()
        find_coupon_feature = find_coupon_feature.strip()
        found_coupon = True
    except AttributeError:
        found_coupon = False

    return found_coupon


def check_if_enhanced_brand_content(html):
    soup = html

    try:
        find_enhanced_brand_content = soup.find('div', attrs={'id': 'aplus3p_feature_div'}).get_text()
        find_enhanced_brand_content = find_enhanced_brand_content.strip()
        find_enhanced_brand_content = True
    except AttributeError:
        find_enhanced_brand_content = False

    return find_enhanced_brand_content


def images_at_least_1000(image_resolution_dict):
    images_less_than_1000 = 0

    for image in image_resolution_dict:
        image_resolution = image_resolution_dict[image]
        image_width = image_resolution[0]
        image_height = image_resolution[1]
        if image_width < 1000 or image_height < 1000:
            images_less_than_1000 += 1
        else:
            continue

    # print("Images less than 1,000: {}".format(images_less_than_1000))

    if images_less_than_1000 == 0:
        return True
    else:
        return False


def calculate_listing_score(image_count_actual, keyword_in_title, overall_review_rating, description_length,
                            top_review_ratings, recent_review_ratings, bullet_length, using_coupon_feature,
                            using_enhanced_brand_content, all_images_1000):
    listing_score = 0

    # image count score
    if 5 <= image_count_actual <= 8:
        listing_score += 4
    elif image_count_actual == 9:
        listing_score += 4  # for having at least 5 images
        listing_score += 3  # for having all 9 images

    # keyword in title
    if keyword_in_title:
        listing_score += 4

    # overall review rating
    if overall_review_rating >= 4.5:
        listing_score += 4
        overall_review_rating_status = "Good"
    else:
        overall_review_rating_status = "{}, Needs Improvement".format(overall_review_rating)

    # description length
    if description_length >= 1500:
        listing_score += 3
        description_length_status = "Good"
    else:
        description_length_status = "{}, Add More Description".format(description_length)

    # top review ratings
    top_ratings = []

    for position in top_review_ratings:
        # print(top_review_ratings[position])
        # rating = float(top_review_ratings[position])
        rating = int(top_review_ratings[position])
        top_ratings.append(rating)

    average_top_rating = round(sum(top_ratings) / len(top_ratings), 1)

    if average_top_rating >= 4.5:
        listing_score += 3
        average_top_rating_status = "Good"
    else:
        average_top_rating_status = "{}, Needs Improvement".format(average_top_rating)

    # recent review ratings
    recent_ratings = []

    if len(recent_review_ratings) == 0:
        average_recent_rating = 0
    else:
        for position in recent_review_ratings:
            # rating = float(recent_review_ratings[position])
            rating = int(recent_review_ratings[position])
            recent_ratings.append(rating)
        average_recent_rating = round(sum(recent_ratings) / len(recent_ratings), 1)

    if average_recent_rating >= 4.5:
        listing_score += 3
        average_recent_rating_status = "Good"
    elif average_recent_rating == 0:
        average_recent_rating_status = "Unable to Scrape"
    else:
        average_recent_rating_status = "{}, Needs Improvement".format(average_recent_rating)

    # bullet length
    bullet_length_list = []

    for bullet in bullet_length:
        length = bullet_length[bullet]
        bullet_length_list.append(length)

    bullet_length_total = sum(bullet_length_list)

    if 500 <= bullet_length_total < 750:
        listing_score += 2
        bullet_length_status = "{}, Add More".format(bullet_length_total)
    elif bullet_length_total >= 750:
        listing_score += 2  # for being over 500
        listing_score += 1  # for being over 750
        bullet_length_status = "Good"
    else:
        bullet_length_status = "{}, Add More".format(bullet_length_total)

    # using coupon feature
    if using_coupon_feature:
        listing_score += 2

    # using Enhanced Brand Content
    if using_enhanced_brand_content:
        listing_score += 1

    # image resolution
    if all_images_1000:
        listing_score += 4

    # todo: add item to score for image properties analysis (beyond just resolution)

    listing_score = int((listing_score * 100) / 34)

    # print()
    # print("Listing score: {}".format(listing_score))

    listing_score_details = {}

    listing_score_details.update({"Listing Score": "{} out of 100".format(listing_score)})

    listing_score_details.update({"Image Count": "{} Unused Image Slots".format(9 - image_count_actual)})

    listing_score_details.update({"All Images Greater than 1,000x1x000": all_images_1000})

    listing_score_details.update({"Main Keyword in Title": keyword_in_title})

    listing_score_details.update({"Overall Review Rating": overall_review_rating_status})

    listing_score_details.update({"Average Top Reviews Rating": average_top_rating_status})

    listing_score_details.update({"Average Recent Reviews Rating": average_recent_rating_status})

    listing_score_details.update({"Total Description Length": description_length_status})

    listing_score_details.update({"Total Bullets Character Count": bullet_length_status})

    listing_score_details.update({"Using Coupon Feature": using_coupon_feature})

    listing_score_details.update({"Using Enhanced Brand Content": using_enhanced_brand_content})

    print()
    print('-----------------------')
    print("Listing Score Details:")
    print('-----------------------')
    print()

    for key in listing_score_details:
        print(key, ": ", listing_score_details[key])

    return listing_score_details
