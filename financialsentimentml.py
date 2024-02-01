# -*- coding: utf-8 -*-
"""FinancialSentimentML.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1P9ZhuodSm17WvqbU2WVsbAhNcGZZ805U
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import random
import spacy
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras import models

import sklearn
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.metrics import make_scorer, classification_report
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.tree import DecisionTreeClassifier
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import cross_validate
from sklearn.metrics import confusion_matrix
import seaborn as sn

!python -m spacy download en_core_web_md

nlp = spacy.load("en_core_web_md")

# Commented out IPython magic to ensure Python compatibility.
# %cd /content/drive/MyDrive/Study/NLP

fcommentDF=pd.read_csv('finan.csv')
fcommentDF = fcommentDF[['Sentence','Sentiment']].dropna()

fcommentDF.head()

plt.figure(figsize=(5, 3.8))
axplot=fcommentDF.Sentiment.value_counts().plot(kind='bar')
plt.xlabel('labels')
plt.ylabel('Number of samples')
axplot.set_xticks(range(3))
axplot.set_xticklabels(['Neural', 'Positive', 'Negative'], rotation=0)
plt.grid()
plt.show()

fcommentDF['sent_len'] = fcommentDF['Sentence'].apply(lambda x: len(x.split(" ")))
max_seq_len = np.round(fcommentDF['sent_len'].mean() + 2 * fcommentDF['sent_len'].std()).astype(int)
max_seq_len

plt.figure(figsize=(5, 3.5))
fcommentDF['sent_len'].plot.hist()
plt.axvline(x=max_seq_len, color='k', linestyle='--', label='max len');
plt.title("Text length distribution")
plt.grid()

label = fcommentDF["Sentiment"]
np.unique(np.array(label), return_counts=True)

def model_report(trained_model):
    y_pred = trained_model.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred)
    print(f"Accuracy: {round(accuracy*100, 2)}%")

    classification_report_result = classification_report(y_test, y_pred)
    print(classification_report_result)

    plot_confusion_matrix(y_pred, y_test, pl=True)

"""## **Data Pre-Processing**

### **NLP**
"""

fcommentDF['processed']= fcommentDF['Sentence'].apply(lambda x: x.lower())
fcommentDF['processed'] = fcommentDF['processed'].apply(lambda x: x.replace('%', 'percent ').replace('$', 'dollar '))
fcommentDF['processed'] = fcommentDF['processed'].str.replace(',', '')

import re
def convert_numeric(match):
    return str(int(float(match.group(0))))

numeric_pattern = r'\b\d+\.\d+\b'  # Assumes floating-point numbers
fcommentDF['processed'] = fcommentDF['processed'].apply(lambda x: re.sub(numeric_pattern, convert_numeric, x))

fcommentDF.head()

"""***Punctuation Removal***"""

import string
string.punctuation
#defining the function to remove punctuation
def remove_punctuation(text):
    punctuationfree="".join([i for i in text if i not in string.punctuation])
    return punctuationfree

fcommentDF['punc_remove']= fcommentDF['processed'].apply(lambda x:remove_punctuation(x))
fcommentDF.head()

"""***tokenization***"""

def tokenization(text):
    mtoks = [token.text for token in nlp(text)]
    return mtoks

fcommentDF['tokennized']= fcommentDF['punc_remove'].apply(lambda x: tokenization(x))

fcommentDF.head()

"""***Remove stop words***"""

import nltk
nltk.download('stopwords')

from nltk.corpus import stopwords
stop_words = stopwords.words('english')

def remove_stopwords(text):
    output= [i for i in text if i not in stop_words]
    return output

fcommentDF['no_stopwords']= fcommentDF['tokennized'].apply(lambda x:remove_stopwords(x))

fcommentDF.head()

"""***Stemming***"""

from nltk.stem.porter import PorterStemmer
porter_stemmer = PorterStemmer()
def stemming(text):
    stem_text = [porter_stemmer.stem(word) for word in text]
    return stem_text

fcommentDF['stemmed']=fcommentDF['no_stopwords'].apply(lambda x: stemming(x))

fcommentDF.head()

"""***Save Pre-processed data***"""

file_name = 'finan_preprocessed.csv'
fcommentDF.to_csv(file_name, sep=',', index=False)

"""### **Data Augmentation**

***Read Processed data***
"""

processedDF=pd.read_csv('finan_preprocessed.csv')
processedDF.head()

processedDF['concatenated_text'] = processedDF['stemmed'].apply(lambda x: ' '.join(eval(x)))

import nltk
nltk.download('wordnet')

from nltk.corpus import wordnet

def get_synonyms(word):
    synonyms = set()

    for syn in wordnet.synsets(word):
        for l in syn.lemmas():
            synonym = l.name().replace("_", " ").replace("-", " ").lower()
            synonym = "".join([char for char in synonym if char in ' qwertyuiopasdfghjklzxcvbnm'])
            synonyms.add(synonym)

    if word in synonyms:
        synonyms.remove(word)

    return list(synonyms)

"""***Replacing with synonyms***"""

finan_sentence_exp = []
aug_categories = []

for idx, rw in processedDF.iterrows():
    tokens = rw["stemmed"]
    rating = rw["Sentiment"]

    augmented_tokens = []

    for token in tokens:
        synonyms = get_synonyms(token)
        if synonyms:
            augmented_tokens.append(random.choice(synonyms))
        else:
            # If no synonyms found, keep the original token
            augmented_tokens.append(token)

    finan_sentence_exp.extend([tokens, augmented_tokens])
    aug_categories.extend([rating, rating])

augmented_df = pd.DataFrame({
    'augmented_data': finan_sentence_exp,
    'rating': aug_categories
})

# Save the DataFrame to a CSV file
augmented_df.to_csv('finan_augmented_data.csv', sep=',', index=False)

"""### **Train-Test Split**

***Load data***
"""

aug_processedDF=pd.read_csv('finan_augmented_data.csv')
aug_processedDF.head()

finan_sentence = []
categories = []

# Perform Tokenization
for idx, fs in aug_processedDF.iterrows():
    comments = fs["augmented_data"]
    sentence = ' '.join(comments)
    rating = fs["rating"]

    if rating == 'positive':
        feel = 1
    elif rating == 'negative':
        feel = 0
    elif rating == 'neutral':
        feel = 2

    categories.append(feel)
    finan_sentence.append(comments)

np.unique(categories, return_counts=True)

"""***TF-IDF***"""

tfidf_vectorizer = TfidfVectorizer(ngram_range=(1,3))
data_tfidf = tfidf_vectorizer.fit_transform(finan_sentence)

"""***Splitting into Train and Test set***"""

from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(data_tfidf, categories, random_state=1, test_size=0.1, shuffle=True)

def plot_confusion_matrix(true_label, predict_label, pl = False):
    categories = ['Neural', 'Positive', 'Negative']
    cm = confusion_matrix(y_true = true_label, y_pred = predict_label)
    cm_per = np.round(cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]*100,2)
    if pl == True:
        df_cm = pd.DataFrame(cm_per, index = categories, columns = categories)
        plt.figure(figsize = (6,5))
        sn.heatmap(df_cm, annot=True, cmap = "Blues", linewidths=.1 ,fmt='.2f')
        plt.title("Confusion matrix")
        plt.xlabel('Predict', fontsize=12)
        plt.ylabel('True', fontsize=12)
        plt.tight_layout()

"""## **Training Models**"""

clf_LR = LogisticRegression(multi_class='ovr', max_iter=1000)
clf_LR.fit(X_train, y_train)

model_report(clf_LR)

"""***SVM***"""

clf_SVM = SVC()
clf_SVM.fit(X_train, y_train)

model_report(clf_SVM)

"""***Multinomial Naive Bayes***"""

clf_NB = MultinomialNB()
clf_NB.fit(X_train, y_train)

model_report(clf_NB)

"""## **Cross Validate the best model**"""

scoring = {'accuracy': 'accuracy',
           'precision_macro': make_scorer(precision_score, average='macro'),
           'recall_macro': make_scorer(recall_score, average='macro'),
           'f1_macro': make_scorer(f1_score, average='macro')}

# Perform cross-validation
cv_results = cross_validate(clf_NB, data_tfidf, categories, cv=5, scoring=scoring)

# Calculate and print the average scores
best_accuracy = np.max(cv_results['test_accuracy'])
best_precision = np.max(cv_results['test_precision_macro'])
best_recall = np.max(cv_results['test_recall_macro'])
best_f1 = np.max(cv_results['test_f1_macro'])

print(f"Best Accuracy: {round(best_accuracy * 100, 2)}%")
print(f"Average Precision (Macro): {round(best_precision * 100, 2)}%")
print(f"Average Recall (Macro): {round(best_recall * 100, 2)}%")
print(f"Average F1 Score (Macro): {round(best_f1 * 100, 2)}%")