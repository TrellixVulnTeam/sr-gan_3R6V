"""
Code for accessing the data in the database easily.
"""
import csv
import cv2
import math
import os
import shutil
import json
import torch
from urllib.request import urlretrieve
import tarfile
import numpy as np
import imageio
from skimage import transform, color
from torch.utils.data import Dataset
from scipy.io import loadmat
from datetime import datetime
import pandas as pd
from tqdm import tqdm
import glob
from utility import to_normalized_range, download_and_extract_file, unison_shuffled_copies, seed_all
from skimage import transform,io
import scipy.misc


class AgeDataset(Dataset):
    """The dataset class for the age estimation application."""
   
    def __init__(self, dataset_path, category,IMAGE_SIZE=1000, start=None, end=None, gender_filter=None, seed=None, batch_size=None):
        self.loadLink = True
        self.has_labels = False
        self.printedItems = 0
        self.image_paths = []
        self.label = []
        self.IMAGE_SIZE = IMAGE_SIZE
        self.category = category
        #Code for new version for the CIL Project
        data_path = './cosmology_aux_data_170429/cosmology_aux_data_170429/'
        self.dataset_path = data_path + category + '/' # Directory of the images
        self.x_images = []
        self.pathBlackImages = '/content/blackImage.jpg'
        try:
          start = start[0]
        except: 
          pass
        try:
            end = end[0]
        except:
            pass
        if start == None:
            start = 0

        
        counter = 0
        if (category == 'query'):
            img_dir = data_path + category + '/' # Directory of the images
            print('Search path: '+ str(img_dir))
            data_path = os.path.join(img_dir,'*g')
            files = glob.glob(data_path)
            print('Length:',len(files))            
            if end == None:
                end = len(files)
            if start < 0:
                start = len(files) + start
            
            for f1 in files:
                #print(counter)

                if self.loadLink:
                    self.image_paths.append(os.path.join(f1))
                else:

                    #print('f1:', f1)
                    img = cv2.imread(f1, cv2.IMREAD_GRAYSCALE)
                    #print('img:',img)
                    resized = cv2.resize(img, (IMAGE_SIZE, IMAGE_SIZE), interpolation=cv2.INTER_AREA)
                    x_images.append(np.array(resized).reshape((IMAGE_SIZE, IMAGE_SIZE, 1)))
            

            if self.loadLink:         
              if end == None:
                self.image_paths = self.image_paths[start:]
              else:
                self.image_paths = self.image_paths[start:end]
              print('Cosmology size of dataset ', category, ': ', len(self.image_paths))
            else:              
              print('Cosmology size of dataset ', category, ': ', len(self.x_images), 'shape: ', self.x_images[1].shape)  
              self.dataset_img = np.array(self.x_images)
              #print('Appended')
              self.dataset_img = self.dataset_img/ 127.5 - 1.
              #print('Normalized')
              
            
            # Labeled images:
            # The folder labeled contains 1200 images. The corresponding labels of each image can be found in <labeled.csv> at the top-level.
            # Make proper use of the scores and labels to build your generative model and learn the similarity function. 
            # Note: We use only the correct labeled ones
        elif ((category == 'labeledTrue')):
            category = "labeled"
            df_labeled = pd.read_csv(data_path + category + '.csv')
            if start < 0:
                start = df_labeled.shape[0] + start

            for index, row in tqdm(df_labeled.iterrows(), total=df_labeled.shape[0]):
                # Only loads the images with score 1 (which are galaxy images)
                if row['Actual'] == 1.0:
                    if self.loadLink:
                        self.image_paths.append(os.path.join(data_path + category + '/' + str(int(row['Id'])) + '.png'))
                    else:
                      img = cv2.imread(data_path + category + '/' + str(int(row['Id'])) + '.png', cv2.IMREAD_GRAYSCALE)
                      resized = cv2.resize(img, (IMAGE_SIZE, IMAGE_SIZE), interpolation=cv2.INTER_AREA)
                      self.x_images.append(nextp.array(resized).reshape((IMAGE_SIZE, IMAGE_SIZE, 1)))

            category = 'Labeled only true'

            if self.loadLink:
              if end == None:
                
                self.image_paths = self.image_paths[start:]
              else:
                
                self.image_paths = self.image_paths[start:end]
              print('Cosmology size of dataset ', category, ': ', len(self.image_paths))
            else:              
              print('Cosmology size of dataset ', category, ': ', len(self.x_images), 'shape: ', self.x_images[1].shape)  
              self.dataset_img = np.array(x_images)
              print('Appended')
              self.dataset_img = self.dataset_img/ 127.5 - 1.
              print('Normalized')

            

        elif ((category == 'labeled')):
            self.has_labels = True
            df_labeled = pd.read_csv(data_path + category + '.csv')
            if start < 0:
                start = df_labeled.shape[0] + start
            for index, row in tqdm(df_labeled.iterrows(), total=df_labeled.shape[0]):
                if self.loadLink:
                    self.image_paths.append(os.path.join(data_path + category + '/' + str(int(row['Id'])) + '.png'))
                    self.label.append(row['Actual'])
                else:
                    img = cv2.imread(data_path + category + '/' + str(int(row['Id'])) + '.png', cv2.IMREAD_GRAYSCALE)
                    resized = cv2.resize(img, (IMAGE_SIZE, IMAGE_SIZE), interpolation=cv2.INTER_AREA)
                    self.x_images.append(np.array(resized).reshape((IMAGE_SIZE, IMAGE_SIZE, 1)))

                #Add black images
                number = 300
                #for i in range(number):
                    
            if self.loadLink:
              if end == None:
                self.label = self.label[start:]
                self.image_paths = self.image_paths[start:]
              else:
                self.label = self.label[start:end]
                self.image_paths = self.image_paths[start:end]
              print('Cosmology size of dataset ', category, ': ', len(self.image_paths), ', labels :',len(self.label))
            else:              
              print('Cosmology size of dataset ', category, ': ', len(self.x_images), 'shape: ', self.x_images[1].shape)  
              self.dataset_img = np.array(self.x_images)
              print('Appended')
              self.dataset_img = self.dataset_img/ 127.5 - 1.
              print('Normalized')
              scores = df_labeled['Actual']
              self.label = scores


            # Scored images:
            # The folder scored contains 9600 images. The majority of these images are realistic cosmology images, whereas some are images of other subjects or corrupted cosmology images.
            # The corresponding similarity scores of each image can be found in <scored.csv> at the top-level.
        elif ((category == 'scored')):
            self.has_labels = True
            df_labeled = pd.read_csv(data_path + category + '.csv')
            if start < 0:
                start = df_labeled.shape[0] + start
            
            for index, row in tqdm(df_labeled.iterrows(), total=df_labeled.shape[0]):
                    # Loads all images
                    if self.loadLink:
                        self.image_paths.append(os.path.join(data_path + category + '/' + str(int(row['Id'])) + '.png'))
                        self.label.append(row['Actual'])
                    else:
                        img = cv2.imread(data_path + category + '/' + str(int(row['Id'])) + '.png', cv2.IMREAD_GRAYSCALE)
                        resized = cv2.resize(img, (IMAGE_SIZE, IMAGE_SIZE), interpolation=cv2.INTER_AREA)
                        self.x_images.append(np.array(resized).reshape((IMAGE_SIZE, IMAGE_SIZE, 1)))
            if self.loadLink:
              if end == None:
                self.label = self.label[start:]
                self.image_paths = self.image_paths[start:]
              else:
                self.label = self.label[start:end]
                self.image_paths = self.image_paths[start:end]
              print('Cosmology size of dataset ', category, ': ', len(self.image_paths))
            else:              
              print('Cosmology size of dataset ', category, ': ', len(self.x_images), 'shape: ', self.x_images[1].shape)  
              self.dataset_img = np.array(self.x_images)
              print('Appended')
              self.dataset_img = self.dataset_img/ 127.5 - 1.
              print('Normalized')
              scores = df_labeled['Actual']
              self.label = scores
        if self.loadLink:
          self.length = len(self.image_paths)
            #print('Length set to ',self.length)
          if len(self.image_paths) < batch_size:
              repeats = math.ceil(batch_size /len(self.image_paths))
              self.image_paths = np.repeat(self.image_paths, repeats)
              try:
                  self.label = np.repeat(self.label, repeats)
              except:
                  pass     
        else:
          self.length = self.dataset_img.shape[0]


   
            
        

        """ # Original Code # ---
        if gender_filter is not None:
            raise NotImplementedError()
        self.dataset_path = dataset_path
        with open(os.path.abspath(os.path.join(self.dataset_path, 'meta.json'))) as json_file:
            json_contents = json.load(json_file)
        image_names, ages = [], []
        for entry in json_contents:
            if isinstance(entry, dict):
                image_names.append(entry['image_name'])
                ages.append(entry['age'])
            else:
                image_name, age, gender = entry
                image_names.append(image_name)
                ages.append(age)
        seed_all(seed)
        image_names, ages = unison_shuffled_copies(np.array(image_names), np.array(ages))
        self.image_names = np.array(image_names[start:end])
        self.ages = np.array(ages[start:end], dtype=np.float32)
        if self.image_names.shape[0] < batch_size:
          repeats = math.ceil(batch_size / self.image_names.shape[0])
          self.image_names = np.repeat(self.image_names, repeats)
          self.ages = np.repeat(self.ages, repeats)
        """

    def __len__(self):
        return self.length


    def __getitem__(self, idx):
        #print("Get item: ",str(idx) +  self.image_paths[idx])
        #print("Label Length",len(self.label))
        #print("Test Length",len(self.test))
        self.printedItems = self.printedItems + 1
        if self.loadLink:
            image_name = self.image_paths[idx]
            image = imageio.imread(os.path.join(image_name))
            image = to_normalized_range(image)
            image = transform.resize(image, (self.IMAGE_SIZE,self.IMAGE_SIZE), mode='symmetric', preserve_range=True)
            #Uncomment and comment the reshape,
            #,if every picture should be done in color mode: Remember to change the dimension in the network from 1 to 3!
            #if len(image.shape) == 2:
            #    image = color.gray2rgb(image)
            #image = image.transpose((2, 0, 1))
            image = image.reshape((1,self.IMAGE_SIZE,self.IMAGE_SIZE))
            image = torch.tensor(image.astype(np.float32))
            if self.label:
              label_image = self.label[idx]
              label_image = torch.tensor(label_image, dtype=torch.float32)
              return image, label_image
            else:
              label_image = idx
              #label_image = torch.tensor(label_image, dtype=torch.float32)
              return image, label_image

        else:
            # Code for CIL Project
            if(self.category == 'query'):
                return dataset_img[idx]
            else:
                return dataset_img[idx],label[idx]
            """
            ----Original Code---
            image_name = self.image_names[idx]
            image = imageio.imread(os.path.join(self.dataset_path, image_name))
            image = image.transpose((2, 0, 1))
            image = torch.tensor(image.astype(np.float32))
            image = to_normalized_range(image)
            age = self.ages[idx]
            age = torch.tensor(age, dtype=torch.float32)
            return image, age

            """
            


class ImdbWikiDatabasePreparer:
    """A class for preparing the IMDB-WIKI database."""
    def __init__(self, preprocessed_image_size=128):
        self.preprocessed_image_size = preprocessed_image_size

    def download_and_preprocess(self):
        """Downloads and preprocesses the database."""
        print('Preparing IMDB-WIKI database.')
        print('Downloading...')
        self.download()
        print('Preprocessing...')
        self.preprocess()

    @staticmethod
    def calculate_age(taken, date_of_birth):
        """Calculates the age of example from the data of birth and photo time stamp."""
        birth_datetime = datetime.fromordinal(max(int(date_of_birth) - 366, 1))
        # Assume the photo was taken in the middle of the year
        if birth_datetime.month < 7:
            return taken - birth_datetime.year
        else:
            return taken - birth_datetime.year - 1

    def get_database_meta(self, mat_path, database_name='imdb', shuffle=True):
        """Gets the meta information of the database."""
        meta = loadmat(mat_path)
        image_paths = np.array(meta[database_name][0, 0]["full_path"][0].tolist())[:, 0]
        dobs = meta[database_name][0, 0]["dob"][0]
        genders = meta[database_name][0, 0]["gender"][0]
        time_stamps = meta[database_name][0, 0]["photo_taken"][0]
        face_scores = meta[database_name][0, 0]["face_score"][0]
        second_face_scores = meta[database_name][0, 0]["second_face_score"][0]
        ages = np.array([self.calculate_age(time_stamps[i], dobs[i]) for i in range(len(dobs))])
        if shuffle:
            p = np.random.permutation(len(ages))
            (image_paths, dobs, genders, time_stamps, face_scores, second_face_scores, ages
             ) = image_paths[p], dobs[p], genders[p], time_stamps[p], face_scores[p], second_face_scores[p], ages[p]
        return image_paths, dobs, genders, time_stamps, face_scores, second_face_scores, ages

    @staticmethod
    def download():
        """Downloads the database."""
        database_directory = '../imdb_wiki_data'
        os.makedirs(database_directory, exist_ok=True)
        crop_database_directory = '../imdb_wiki_data/imdb_crop'
        if os.path.exists(crop_database_directory):
            shutil.rmtree(crop_database_directory)
        os.makedirs(crop_database_directory)
        urlretrieve('https://data.vision.ee.ethz.ch/cvl/rrothe/imdb-wiki/static/imdb_crop.tar',
                    os.path.join(database_directory, 'imdb_crop.tar'))
        with tarfile.open(os.path.join(database_directory, 'imdb_crop.tar')) as tar_file:
            def is_within_directory(directory, target):
                
                abs_directory = os.path.abspath(directory)
                abs_target = os.path.abspath(target)
            
                prefix = os.path.commonprefix([abs_directory, abs_target])
                
                return prefix == abs_directory
            
            def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
            
                for member in tar.getmembers():
                    member_path = os.path.join(path, member.name)
                    if not is_within_directory(path, member_path):
                        raise Exception("Attempted Path Traversal in Tar File")
            
                tar.extractall(path, members, numeric_owner=numeric_owner) 
                
            
            safe_extract(tar_file, path=database_directory)
            os.remove(os.path.join(database_directory, 'imdb_crop.tar'))
        print('Done.')

    def preprocess(self):
        """Preprocesses the database to the format needed by the network."""
        preprocessed_directory = '../imdb_wiki_data/imdb_preprocessed_{}'.format(self.preprocessed_image_size)
        if os.path.exists(preprocessed_directory):
            shutil.rmtree(preprocessed_directory)
        os.makedirs(preprocessed_directory)
        mat_path = '../imdb_wiki_data/imdb_crop/imdb.mat'
        dataset_base = '../imdb_wiki_data/imdb_crop/'
        # Get viable examples.
        (image_paths, dobs, genders, time_stamps, face_scores, second_face_scores, ages
         ) = self.get_database_meta(mat_path)
        indexes = []
        for index, image_path in enumerate(image_paths):
            if face_scores[index] < 1.0:
                continue
            if (~np.isnan(second_face_scores[index])) and second_face_scores[index] > 0.0:
                continue
            if ~(10 <= ages[index] <= 95):
                continue
            if np.isnan(genders[index]):
                continue
            try:
                image = imageio.imread(os.path.join(dataset_base, image_path))
            except FileNotFoundError:
                continue
            if image.shape[0] < 256 or image.shape[1] < 256 or abs(image.shape[0] - image.shape[1]) > 5:
                continue
            indexes.append(index)
        image_paths = image_paths[indexes]
        ages = ages[indexes].astype(np.float32).tolist()
        genders = genders[indexes].tolist()
        # Preprocess images and create JSON.
        json_list = []
        for image_path, age, gender in zip(image_paths, ages, genders):
            image = imageio.imread(os.path.join(dataset_base, image_path))
            image = transform.resize(image, (self.preprocessed_image_size, self.preprocessed_image_size),
                                     preserve_range=True)
            if len(image.shape) == 2:
                image = color.gray2rgb(image)
            image_name = os.path.basename(image_path)
            imageio.imsave(os.path.join(preprocessed_directory, image_name), image.astype(np.uint8))
            gender = {0: 'female', 1: 'male'}[gender]
            json_list.append([image_name, age, gender])
        with open(os.path.join(preprocessed_directory, 'meta.json'), 'w+') as json_file:
            json.dump(json_list, json_file)


class LapDatabasePreparer:
    """A class to prepare the LAP V2 Apparent Age database."""
    def __init__(self, preprocessed_image_size=128):
        from mtcnn.mtcnn import MTCNN
        self.database_directory = '../LAP Apparent Age V2'
        self.face_detector = MTCNN(steps_threshold=[0.5, 0.6, 0.6])
        self.preprocessed_image_size = preprocessed_image_size

    def download_and_preprocess(self):
        """Downloads and preprocesses the database."""
        print('Preparing LAP Apparent Age V2 database.')
        print('Downloading...')
        self.download()
        print('Preprocessing...')
        self.preprocess()

    def download(self):
        """Downloads the database."""
        if os.path.exists(self.database_directory):
            shutil.rmtree(self.database_directory)
        os.makedirs(self.database_directory)
        os.makedirs(os.path.join(self.database_directory, 'train'))
        os.makedirs(os.path.join(self.database_directory, 'validation'))
        os.makedirs(os.path.join(self.database_directory, 'test'))
        download_and_extract_file(os.path.join(self.database_directory, 'train'),
                                  'http://158.109.8.102/ApparentAgeV2/train_1.zip', 'train1.zip')
        download_and_extract_file(os.path.join(self.database_directory, 'train'),
                                  'http://158.109.8.102/ApparentAgeV2/train_2.zip', 'train2.zip')
        download_and_extract_file(os.path.join(self.database_directory, 'train'),
                                  'http://158.109.8.102/ApparentAgeV2/train_gt.zip', 'train_gt.zip')
        download_and_extract_file(os.path.join(self.database_directory, 'validation'),
                                  'http://158.109.8.102/ApparentAgeV2/valid.zip', 'valid.zip')
        # noinspection SpellCheckingInspection
        download_and_extract_file(os.path.join(self.database_directory, 'validation'),
                                  'http://158.109.8.102/ApparentAgeV2/valid_gt.zip', 'valid_gt.zip',
                                  password=b'Aj9WUCc5LJagn4')
        download_and_extract_file(os.path.join(self.database_directory, 'test'),
                                  'http://158.109.8.102/ApparentAgeV2/test_1.zip', 'test1.zip',
                                  password=b'0PWW7nh@5wTuAS')
        download_and_extract_file(os.path.join(self.database_directory, 'test'),
                                  'http://158.109.8.102/ApparentAgeV2/test_2.zip', 'test2.zip',
                                  password=b'0PWW7nh@5wTuAS')
        download_and_extract_file(os.path.join(self.database_directory, 'test'),
                                  'http://158.109.8.102/ApparentAgeV2/test_gt.zip', 'test_gt.zip',
                                  password=b'0PWW7nh@5wTuAS')

    def preprocess(self):
        """Preprocesses the database to the format needed by the network."""
        preprocessed_directory = os.path.join(self.database_directory,
                                              'preprocessed_{}'.format(self.preprocessed_image_size))
        if os.path.exists(preprocessed_directory):
            shutil.rmtree(preprocessed_directory)
        os.makedirs(preprocessed_directory)
        for data_type in ['train', 'validation', 'test']:
            preprocessed_data_type_directory = os.path.join(preprocessed_directory, data_type)
            os.makedirs(preprocessed_data_type_directory)
            for item in os.listdir(os.path.join(self.database_directory, data_type)):
                item_path = os.path.join(self.database_directory, data_type, item)
                if item.startswith('.'):
                    continue
                elif item.endswith('.jpg'):
                    item_directory = os.path.dirname(item_path)
                    self.crop_image_to_face(item_directory, item, preprocessed_data_type_directory)
                elif os.path.isdir(item_path):
                    for image_name in os.listdir(item_path):
                        if not image_name.endswith('.jpg'):
                            raise NotImplementedError()
                        self.crop_image_to_face(item_path, image_name, preprocessed_data_type_directory)
                elif item.endswith('_gt.csv'):
                    with open(item_path) as csv_file:
                        csv_reader = csv.reader(csv_file)
                        json_list = []
                        next(csv_reader)  # Skip header line.
                        for csv_line in csv_reader:
                            image_name, age, age_standard_deviation = csv_line
                            example_meta_dict = {'image_name': image_name, 'age': age,
                                                 'age_standard_deviation': age_standard_deviation}
                            json_list.append(example_meta_dict)
                    with open(os.path.join(preprocessed_data_type_directory, 'meta.json'), 'w+') as json_file:
                        json.dump(json_list, json_file)

    def crop_image_to_face(self, directory, image_name, output_directory):
        """Crops an image to the detected face."""
        image_path = os.path.join(directory, image_name)
        image = imageio.imread(image_path, pilmode='RGB')
        detected_faces = self.face_detector.detect_faces(image)
        if len(detected_faces) == 0:
            cropped_image = image
            print('Failed for {}. Image was stretched and not cropped.'.format(image_path))
        else:
            detected_faces = sorted(detected_faces, key=lambda item: item['confidence'], reverse=True)
            x, y, width, height = detected_faces[0]['box']
            center_x = x + int(width / 2)
            center_y = y + int(height / 2)
            longer_side_length = max(width, height)
            margin_multiplier = 1.2
            half_crop_size = int((longer_side_length * margin_multiplier) / 2)
            crop_x_start = center_x - half_crop_size
            crop_x_end = center_x + half_crop_size
            crop_y_start = center_y - half_crop_size
            crop_y_end = center_y + half_crop_size
            unchecked_crop_box = [crop_y_start, crop_x_start, crop_y_end, crop_x_end]
            crop_x_start = max(crop_x_start, 0)
            crop_y_start = max(crop_y_start, 0)
            crop_x_end = min(crop_x_end, image.shape[1])
            crop_y_end = min(crop_y_end, image.shape[0])
            crop_box = [crop_y_start, crop_x_start, crop_y_end, crop_x_end]
            if unchecked_crop_box != crop_box:
                print('Bad crop for {}. Cropped image is stretched.'.format(image_path))
            cropped_image = image[crop_y_start:crop_y_end, crop_x_start:crop_x_end]
        cropped_image = transform.resize(cropped_image, (self.preprocessed_image_size, self.preprocessed_image_size),
                                         preserve_range=True)
        imageio.imwrite(os.path.join(output_directory, image_name), cropped_image.astype(np.uint8))

