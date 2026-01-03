# Crawl national exam grades of all provinces in VN
### [REQUIREMENTS]
You must have the API (always a GET method) to form the data source

API in this sample: 

```
"https://vietnamnet.vn/newsapi-edu/EducationStudentScore/CheckCandidateNumber"
```
Set up neccessary libs (sorry im lazy in creating a requirement.txt)
```
pip install aiohttp asyncio tqdm
```
Run:
```
python crawl.py
```

Anyways, this github repo help you crawl all data from an open-hidden source ( hide the id ), do not practise with the given API call ( the API give you all the data sources without hidden pieces, eg: API in a commercial website, ...) because it is trivial and nonsense :D 

PEACE, good luck
