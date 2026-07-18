from typing import Optional
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class RagPublikasiBRS(BaseModel):
    id: str
    type: str
    bps_id: str
    title: str 
    halaman: int
    content: str
    rl_date: str
    file_path: str
    score: float
    jawaban: str = ''
    def print(self):
        if self.jawaban != '':
            return self.print_jawaban()


        rl_date_split = self.rl_date.split("-")
        if self.type == 'pub' :
            return f"""ID Pengetahuan :  {self.id}
jenis : internal
Judul : {self.title}
Data : {self.content}
Release : {self.rl_date}
Link : https://sulbar.bps.go.id/id/publication/{rl_date_split[0]}/{rl_date_split[1]}/{rl_date_split[2]}/{self.bps_id}/pub.html
Score : {self.score}
"""
        elif  self.type == 'brs' : 
            return f"""ID Pengetahuan :  {self.id}
jenis : internal
Judul : {self.title}
Data : {self.content}
Release : {self.rl_date}
Link : https://sulbar.bps.go.id/id/pressrelease/{rl_date_split[0]}/{rl_date_split[1]}/{rl_date_split[2]}/{self.bps_id}/pub.html
Score : {self.score}
"""
    def print_jawaban(self):
        rl_date_split = self.rl_date.split("-")
        if self.type == 'pub' :
            return f"""ID Pengetahuan :  {self.id}
jenis : internal
Judul : {self.title}
Data : {self.jawaban}
Release : {self.rl_date}
Link : https://sulbar.bps.go.id/id/publication/{rl_date_split[0]}/{rl_date_split[1]}/{rl_date_split[2]}/{self.bps_id}/pub.html
Score : {self.score}
"""
        elif  self.type == 'brs' : 
            return f"""ID Pengetahuan :  {self.id}
jenis : internal
Judul : {self.title}
Data : {self.jawaban}
Release : {self.rl_date}
Link : https://sulbar.bps.go.id/id/pressrelease/{rl_date_split[0]}/{rl_date_split[1]}/{rl_date_split[2]}/{self.bps_id}/pub.html
Score : {self.score}
"""

class RagData(BaseModel):
    id: str
    judul: str 
    url: str
    content: str
    score: float
    jawaban: str = ''
    def print(self):
        if self.jawaban != '':
            return self.print_jawaban()

        return f"""ID Pengetahuan :  {self.id}
jenis : internal
Judul : {self.judul}
Data : {self.content}
Url : {self.url}
Score : {self.score}
"""
    def print_jawaban(self):
        return f"""ID Pengetahuan :  {self.id}
jenis : internal
Judul : {self.judul}
Data : {self.jawaban}
Url : {self.url}
Score : {self.score}
"""

    
    
class RagRilisPublikasi(BaseModel):
    id: str
    tipe: str
    bps_id: str
    rl_date: str
    content: str
    score: float
    def print(self):
        rl_date_split = self.rl_date.split("-")
        if self.tipe == 'publication' :
            return f"""ID Pengetahuan :  {self.id}
jenis : internal
tipe : {self.tipe}
Data : {self.content}
Release : {self.rl_date}
Link : https://sulbar.bps.go.id/id/publication/{rl_date_split[0]}/{rl_date_split[1]}/{rl_date_split[2]}/{self.bps_id}/pub.html
Score : {self.score}
"""
        elif  self.tipe == 'pressrelease' : 
            return f"""ID Pengetahuan :  {self.id}
jenis : internal
tipe : {self.tipe}
Data : {self.content}
Release : {self.rl_date}
Link : https://sulbar.bps.go.id/id/pressrelease/{rl_date_split[0]}/{rl_date_split[1]}/{rl_date_split[2]}/{self.bps_id}/pub.html
Score : {self.score}
"""
    
class DDGS(BaseModel):
    id: str
    snippet: str 
    title: str
    link: str
    score: float = 0.0
    jawaban: str = ''
    def print(self):
        if self.jawaban != '':
            return self.print_jawaban()
        return f"""ID Pengetahuan :  {self.id}
jenis : search
Judul : {self.title}
Data : {self.snippet}
Url : {self.link}
Score : {self.score}
"""
    def print_jawaban(self):
        return f"""ID Pengetahuan :  {self.id}
jenis : search
Judul : {self.title}
Data : {self.jawaban}
Url : {self.link}
Score : {self.score}
"""

class AnswerModel(BaseModel):
    type: str #file, text, system
    file_path: Optional[str] = None
    text: Optional[str] = None
    sitasi: list[str] = []

class QuestionModel(BaseModel):
    ques: Optional[str] = None
    rag_ques: list[str] = []
    keyword: list[str] = []
    answer: list[AnswerModel] = []
    rag_publikasi_brs: list[RagPublikasiBRS] = []
    rag_data: list[RagData] = []
    rag_rilis_publikasi: list[RagRilisPublikasi] = []
    ddgs: list[DDGS] = []
    urutan_rag: list[str] = []
    rag_publikasi_brs_output: list[RagPublikasiBRS] = []
    rag_data_output: list[RagData] = []
    rag_rilis_publikasi_output: list[RagRilisPublikasi] = []
    ddgs_output: list[DDGS] = []
    

class ChatMessage(BaseModel):
    role: str
    content: str