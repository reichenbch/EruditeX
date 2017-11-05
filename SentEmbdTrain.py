from Helpers import utils
import numpy as np
import os
import pickle
import sys
from Models import SentEmbd
import datetime
import time

BASE = os.path.dirname(os.path.abspath(__file__))

def read_dataset():
    #PreProcessing of Data before training our SentEmbd Model includes converting of words to their vector representation
    training_set=os.path.join(os.path.join(BASE,'data'),"SICK.txt")
    with open(training_set,'r') as file1:
        raw_dataset=file1.read().split('\n')
    file1.close()
    # print(raw_dataset) #TESTING PURPOSE
    dataset=[]
    training_dataset=[]
    sim_dataset=[]
    relatedness_scores=[]
    raw_dataset=raw_dataset[1:-1]
    for item in raw_dataset:
        temp=item.split('\t')
        temp2=temp[4]
        temp=temp[1:3]
        temp.append(temp2)
        dataset.append(temp)

    glove=utils.load_glove()

    for item in dataset:
        sent1=item[0].split(' ')
        sent2=item[1].split(' ')
        sent_1=[]
        sent_2=[]
        for word in sent1:
            sent_1.append(utils.get_vector(word,glove))
        for word in sent2:
           sent_2.append(utils.get_vector(word,glove))
        training_dataset.append(sent_1)
        sim_dataset.append(sent_2)
        relatedness_scores.append(float(item[2]))
    return dataset,training_dataset,sim_dataset,relatedness_scores

def main():
    n=int(sys.argv[1])
    hid_dim=int(sys.argv[3])
    dataset,training_dataset,sim_dataset,relatedness_scores = read_dataset()
    sent_embd=SentEmbd.SentEmbd(50,hid_dim) #GRU INITIALIZED
    batch_size=1 #By default
    epochs=int(sys.argv[2])
    test = sys.argv[4]

    start = time.time()
    sent_embd.trainx(training_dataset[:n],sim_dataset[:n],relatedness_scores[:n],epochs) #Training THE GRU using the SICK dataset

    print("Time taken for training:\t"+str(time.time()-start))

    z=str(datetime.datetime.now()).split(' ')

    #To Check for accuracy after training.
    acc="Nan"
    if test == 'test':
        file_name = "SentEmbd_"+str(epochs)+"_"+str(n)+"_"+str(hid_dim)+"_"+z[0]+"_"+z[1].split('.')[0]+".txt"
        path = os.path.join(os.path.join(os.path.join(BASE,'logs'),'SentEmbd'),file_name)
        accuracy=sent_embd.testing(training_dataset[n+1:],sim_dataset[n+1:],relatedness_scores[n+1:],path)
        acc="{0:.3}".format(accuracy)
        acc+="%"

    # Saving the trained Model:
    
    # print(z)
    file_name="SentEmbd_"+str(epochs)+"_"+str(n)+"_"+str(hid_dim)+"_"+acc+"_"+z[0]+"_"+z[1].split('.')[0]+".pkl"
    path = os.path.join(os.path.join(os.path.join(BASE,'states'),'SentEmbd'),file_name)
    sent_embd.save_params(path,epochs)



    print("Current model params saved in- ",file_name)



if __name__ == '__main__':
    main()
