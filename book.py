import streamlit as st
import requests
import pandas as pd
import json
import pymysql

# Google Books API Key
API_KEY = "AIzaSyCOgpwd6VAjL8YsmnoTJ336w0EjWrm8P6E"

# MySQL Database Configuration
DB_CONFIG = {
    'host': 'localhost',       #  MySQL server address
    'user': 'root',            #  MySQL username
    'password': 'nandha1510',  #  MySQL password
    'database': 'guviproject'   # desired database name
}




# Save data to the MySQL database
def save_to_db(data):
    
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        for record in data:
            cursor.execute('''
            INSERT INTO books (
             search_key, book_title, book_subtitle, book_authors, book_description,
            industryIdentifiers, text_readingModes, image_readingModes, pageCount, categories,
            language, imageLinks, ratingsCount, averageRating, country, saleability,
            isEbook, amount_listPrice, amount_retailPrice, currencyCode_listPrice, currencyCode_retailPrice, buyLink, year
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''',(
            record['Search Key'], record['Book Title'], record['Subtitle'], record['Authors'],
            record['Description'], record['Industry Identifiers'], record['Text Reading Mode'],
            record['Image Reading Mode'], record['Page Count'], record['Categories'],
            record['Language'], record['Image Links'], record['Ratings Count'], record['Average Rating'],
            record['Country'], record['Saleability'], record['Is Ebook'], record['Amount List Price'],
            record['Amount Retail Price'], record['Currency Code List Price'], record['Currency Code Retail Price'], 
            record['Buy Link'], record['Year']
    ))

        conn.commit()
        conn.close()
    

# Fetch books for a given query and category
def fetch_books(api_key, category, max_results=40, start_index=0):
    base_url = "https://www.googleapis.com/books/v1/volumes"
    params = {
        'q': category,
        'maxResults': max_results,
        'startIndex': start_index,
        'key': api_key,
        'projection': 'full',
    }
    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Error: {response.status_code} - {response.text}")
        return None

# Fetch all books for all categories
def fetch_all_categories(api_key, categories, total_books=500):
    st.write (categories)
    books_data = []
    
    for start_index in range(0, total_books, 40):
        data = fetch_books(api_key, categories, max_results=40, start_index=start_index)
        
        if data and 'items' in data:
            for book in data['items']:
                books_data.append(extract_book_details(book, category))
        else:
            break
    return books_data

# Extract book details
def extract_book_details(book, category):
    volume_info = book.get('volumeInfo', {})
    sale_info = book.get('saleInfo', {})
    industry_identifiers = volume_info.get('industryIdentifiers', [])
    return {
        'Search Key': category,
        'Book Title': volume_info.get('title', 'N/A'),
        'Subtitle': volume_info.get('subtitle', 'N/A'),
        'Authors': ', '.join(volume_info.get('authors', ['Unknown'])),
        'Description': volume_info.get('description', 'N/A'),
        'Industry Identifiers': json.dumps(industry_identifiers),
        'Text Reading Mode': int(volume_info.get('readingModes', {}).get('text', False)),
        'Image Reading Mode': int(volume_info.get('readingModes', {}).get('image', False)),
        'Page Count': volume_info.get('pageCount', 0),  
        'Categories': ', '.join(volume_info.get('categories', ['Unknown'])),
        'Language': volume_info.get('language', 'N/A'),
        'Image Links': volume_info.get('imageLinks', {}).get('thumbnail', 'N/A'),
        'Average Rating': volume_info.get('averageRating', 0.0),  
        'Ratings Count': volume_info.get('ratingsCount', 0),
        'Country': sale_info.get('country', 'N/A'),
        'Amount List Price': sale_info.get('listPrice', {}).get('amount', 0.0),  
        'Amount Retail Price': sale_info.get('retailPrice', {}).get('amount', 0.0),
        'Sale Price': sale_info.get('salePrice', {}).get('amount', 'N/A'),
        'Currency Code List Price': sale_info.get('listPrice', {}).get('currencyCode', 'N/A'),
        'Currency Code Retail Price': sale_info.get('retailPrice', {}).get('currencyCode', 'N/A'),
        'Saleability': sale_info.get('saleability', 'N/A'),
        'Is Ebook': int(sale_info.get('isEbook', False)),
        'Buy Link': sale_info.get('buyLink', 'N/A'),
        'Year': volume_info.get('publishedDate', 'N/A'),
        
    }

# Categories
CATEGORIES = [
    "fiction", "science", "technology", "history", "biography",
    "art", "philosophy", "education", "mathematics", "health"
]

def load_data(query):
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query)
    result = cursor.fetchall()
    conn.close()
    return pd.DataFrame(result)

QUERIES = {
    "Availability of eBooks vs Physical Books": """
            SELECT isEbook, COUNT(*) as count FROM books GROUP BY isEbook
        """,
        "Top Publishers by Book Count": """
            SELECT saleability, COUNT(*) as count FROM books GROUP BY saleability ORDER BY count DESC LIMIT 10
        """,
        
        "Publisher with Highest Rating (10+ Books)": """
            SELECT saleability, AVG(averageRating) as avg_rating, COUNT(*) as book_count 
            FROM books GROUP BY saleability HAVING COUNT(*) > 10 ORDER BY avg_rating DESC LIMIT 1
        """,
         "Top 5 Most Expensive Books by Retail Price": """
            SELECT book_title, amount_retailPrice, currencyCode_retailPrice FROM books WHERE amount_retailPrice IS NOT NULL ORDER BY 
            amount_retailPrice DESC 
        LIMIT 5;
    """,
         "Books with Discounts > 20%": """
        SELECT 
            book_title, 
            amount_listPrice, 
            amount_retailPrice, 
            ROUND(((amount_listPrice - amount_retailPrice) / amount_listPrice) * 100, 2) AS discount_percentage 
        FROM 
            books 
        WHERE 
            amount_listPrice > 0 
            AND amount_retailPrice > 0 
            AND ((amount_listPrice - amount_retailPrice) / amount_listPrice) * 100 > 20;
    """,
        "Average Page Count for eBooks vs Physical Books": """
    SELECT 
        isEbook, 
        AVG(pageCount) AS avg_page_count 
    FROM 
        books 
    WHERE 
        pageCount > 0 
    GROUP BY 
        isEbook;
""",
    "Top 3 Authors with the Most Books": """
    SELECT 
        book_authors, 
        COUNT(*) AS book_count 
    FROM 
        books 
    WHERE 
        book_authors IS NOT NULL 
    GROUP BY 
        book_authors 
    ORDER BY 
        book_count DESC 
    LIMIT 3;
""",
   "Publishers with More than 10 Books": """
    SELECT 
        saleability AS publisher, 
        COUNT(*) AS book_count 
    FROM 
        books 
    GROUP BY 
        saleability 
    HAVING 
        COUNT(*) > 10 
    ORDER BY 
        book_count DESC;
""",
    "Average Page Count for Each Category": """
    SELECT 
        categories, 
        AVG(pageCount) AS avg_page_count 
    FROM 
        books 
    WHERE 
        categories IS NOT NULL AND pageCount > 0 
    GROUP BY 
        categories 
    ORDER BY 
        avg_page_count DESC;
""",
    "Books with More than 3 Authors": """
    SELECT 
        book_title, 
        book_authors 
    FROM 
        books 
    WHERE 
        LENGTH(book_authors) - LENGTH(REPLACE(book_authors, ',', '')) + 1 > 3;
""",
    "Books with Ratings Count Greater Than the Average": """
    SELECT 
        book_title, 
        ratingsCount 
    FROM 
        books 
    WHERE 
        ratingsCount > (SELECT AVG(ratingsCount) FROM books);
""",
    "Books with the Same Author Published in the Same Year": """
    SELECT 
        book_authors, 
        year, 
        COUNT(*) AS book_count 
    FROM 
        books 
    WHERE 
        year IS NOT NULL AND book_authors IS NOT NULL 
    GROUP BY 
        book_authors, year 
    HAVING 
        COUNT(*) > 1;
""",
    "Year with the Highest Average Book Price": """
    SELECT 
        year, 
        AVG(amount_retailPrice) AS avg_price 
    FROM 
        books 
    WHERE 
        amount_retailPrice > 0 
    GROUP BY 
        year 
    ORDER BY 
        avg_price DESC 
    LIMIT 1;
""",
    "Count Authors Who Published 3 Consecutive Years": """
    SELECT 
        book_authors, 
        GROUP_CONCAT(DISTINCT year ORDER BY year) AS years 
    FROM 
        books 
    WHERE 
        year IS NOT NULL 
    GROUP BY 
        book_authors 
    HAVING 
        FIND_IN_SET('2019', years) AND FIND_IN_SET('2020', years) AND FIND_IN_SET('2021', years);
""",
    
    "Authors Who Published in Same Year but Under Different Publishers": """
        SELECT 
            book_authors, 
            year, 
            COUNT(DISTINCT saleability) AS publisher_count, 
            COUNT(*) AS book_count 
        FROM 
            books 
        WHERE 
            book_authors IS NOT NULL 
            AND year IS NOT NULL 
            AND saleability IS NOT NULL 
        GROUP BY 
            book_authors, year 
        HAVING 
            COUNT(DISTINCT saleability) > 1;
    """,
    "Average Retail Price of eBooks and Physical Books": """
        SELECT 
            AVG(CASE WHEN isEbook = TRUE THEN amount_retailPrice ELSE NULL END) AS avg_ebook_price, 
            AVG(CASE WHEN isEbook = FALSE THEN amount_retailPrice ELSE NULL END) AS avg_physical_price 
        FROM 
            books 
        WHERE 
            amount_retailPrice IS NOT NULL;
    """,
    "Books with Ratings Two Standard Deviations Away from the Average": """
        WITH rating_stats AS (
            SELECT 
                AVG(averageRating) AS avg_rating, 
                STDDEV(averageRating) AS stddev_rating 
            FROM 
                books 
            WHERE 
                averageRating IS NOT NULL
        )
        SELECT 
            book_title, 
            averageRating, 
            ratingsCount 
        FROM 
            books, rating_stats 
        WHERE 
            averageRating IS NOT NULL 
            AND (averageRating > avg_rating + 2 * stddev_rating 
                 OR averageRating < avg_rating - 2 * stddev_rating);
    """,
    "Publisher with Highest Average Rating (More Than 10 Books)": """
        SELECT 
            saleability AS publisher, 
            AVG(averageRating) AS avg_rating, 
            COUNT(*) AS book_count 
        FROM 
            books 
        WHERE 
            averageRating IS NOT NULL 
        GROUP BY 
            saleability 
        HAVING 
            COUNT(*) > 10 
        ORDER BY 
            avg_rating DESC 
        LIMIT 1;
    """,
    
    
}



# Streamlit App

st.sidebar.title("Navigation")
page = st.sidebar.selectbox("Choose a page", ["Home", "Fetch", "Analysis"])

if page == "Home":
    st.title("Google Books API Project with MySQL Integration")
    st.write("""
    - *Home*: Overview of the project  
    - *Fetch*: Fetch books from categories and store in the database  
    - *Analysis*: Perform SQL queries on the fetched data  
    """)

elif page == "Fetch":
    st.title("Fetch Books")
    #st.write("Fetching books for the following categories:")
    #st.write(", ".join(CATEGORIES))
    category=st.text_input("enter your book category")
    if st.button("Fetch Books"):
        books_data = fetch_all_categories(API_KEY, category, total_books=500)
        st.write(books_data)
        save_to_db(books_data)
        st.success("Books fetched and saved to the database!")

elif page == "Analysis":
    st.title("Analysis")
    st.write("Select a query from the dropdown to analyze data:")
    query_choice = st.selectbox("Select Query", list(QUERIES.keys()))
    if st.button("Show Results"):
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        query_sql = QUERIES[query_choice]
        cursor.execute(query_sql)
        result = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        df = pd.DataFrame(result, columns=columns)
        st.dataframe(df)
        conn.close()