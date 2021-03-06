import subprocess
import os
import nltk.data
import threading

from flask import Flask
from flask import Response
from flask import request
from flask import jsonify
from flask_cors import CORS
from werkzeug import secure_filename

from Helpers import file_extraction
from Helpers import deployment_utils as deploy
from IR import infoRX
from Models import abcnn_model
from Models import AnsSelect
from Models import DT_RNN

class EdXServer():

    status = {}

    def __init__(self):
        self.file = ''
        self.context = []
        self.query = ''

    @classmethod
    def update(cls, value):
        cls.status = value

    def get_file(self, filename):

        # print(filename)
        self.file = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        self.context = file_extraction.extract_file_contents(self.file)
        print(self.context)
        if len(self.context) > 0:
            self.context = self.context[0]
            return True
        
        return False

        # return True #TODO: remove before deployment

    def get_query(self, query):
        
        self.query = query
        print(self.query)

        # Filter top 5 paras using Info Retrieval
        self.update({'val': 'Ranking Paragraphs using Information Retrieval.'})
        para_select = infoRX.retrieve_info(self.context, self.query)
        para_sents = []
        tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')

        print(type(para_select[0]), para_select[0])

        self.update({'val': 'Tokenizing top ranked paragraphs'})
        for para in para_select:
            para_sents.extend(tokenizer.tokenize(para[0]))

        print('Sentences selected by IR Module:')
        print(para_sents)
        
        val_list = []
        for sent in para_sents:
            val_list.append({'word': sent, 'score': '\b\b'})
        self.update({'val': 'Sentences selected by IR Module', 'answers': val_list})

        try:
            # Select Ans Sents - ABCNN
            self.update({'val': 'Ranking Candidate Answer Sentences.'})
            abcnn = abcnn_model()
            ans_sents = abcnn.ans_select(query, para_sents)
            
            val_list = []
            for sentence,score in ans_sents:
                val_list.append({'word': sentence, 'score': score[0]})              
            self.update(
                {
                    'val': 'Sentences scored by Sentence Selection Module', 
                    'answers': val_list,
                },
            )

            print('\nSystem: Sentences scored by Sentence Selection Module')
            for sentence,score in ans_sents:
                print('{0:50}\t{1}'.format(sentence, score[0]))
            print('')

            self.update({'val': 'Generating VDT and extracting Answer.'})
            best_ans, score, answers = deploy.extract_answer_from_sentences(
                ans_sents,
                query,
                verbose=True,
            )

        except Exception as e:

            return {'answers': [{'word': 'ERROR', 'score': str(e)}]}


        # Ignore: Phase 2-3: Input Module and Answer Module
        # answers = []
        # for ans, a_score in ans_sents.iteritems():
        #   words = deploy.extract_answer_from_sentence(ans, self.query)
        #   words = sorted(words, key=operator.itemgetter(1))
        #   for word, w_score in words.iteritems()[:5]:
        #       answers.append((word, w_score * a_score))
        # answers = sorted(answers, key=operator.itemgetter(1))
        # proc = subprocess.Popen(['python','test.py',query],shell=False,stdout=subprocess.PIPE)

        ans_list = []
        print('\nSystem: Candidate answers scored by Answer Extraction Module')
        for x in answers[:5]:
            print('{0:10}\t{1}'.format(x[0], float(x[1][0])))
            ans_list.append({'word':x[0], 'score': float(x[1][0])})

        ans_dict = {'val': 'Candidate answers scored by Answer Extraction Module', 'answers': ans_list}

        return ans_dict


app = Flask(__name__)
app2 = Flask(__name__)
server = EdXServer()

CORS(app, origins="http://localhost:5000", allow_headers=[
    "Content-Type", "Authorization", "Access-Control-Allow-Origin"],
    supports_credentials=True, intercept_exceptions=False)

CORS(app2, origins="http://localhost:5001", allow_headers=[
    "Content-Type", "Authorization", "Access-Control-Allow-Origin"],
    supports_credentials=True, intercept_exceptions=False)

app.config['UPLOAD_FOLDER'] = os.path.join('./data/uploads')

@app.route('/filed',methods=['POST'])
def filer():
    print('here')
    # data = request.get_json(force=True)
    # filename = data['filename']
    # file = data['file']
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
        
    f = request.files['file']
    f.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename)))
    print(f)

    if server.get_file(f.filename):
        resp = Response('File uploaded. Context Ready.')
    else:
        resp = Response('Error in file upload.')

    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

@app2.route('/query',methods=['POST'])
def queried():
    query = request.get_json(force=True)['query']
    # resp = Response(server.get_query(query))
    resp = jsonify(server.get_query(query))
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

@app.route('/status', methods=['POST'])
def status():
	print(EdXServer.status)
	resp = jsonify(EdXServer.status)
	resp.headers['Access-Control-Allow-Origin'] = '*'
	return resp

def start1(port):
    app.run(port=port)

def start2(port):
    app2.run(port=port)

if __name__ == '__main__':
    t1 = threading.Thread(target=start1, args=(5000,))
    t2 = threading.Thread(target=start2, args=(5001,))
    t1.start()
    t2.start()
