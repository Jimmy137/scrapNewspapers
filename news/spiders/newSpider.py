import scrapy
from scrapy import Request
from ..items import NewsItem
import json

def inputs(keyword, st_date = None, end_date = None, state_two_letters = None, county = None):
    keyword_lst = keyword.split(' ')
    kw = '+'.join(keyword_lst)
    url = f'https://www.newspapers.com/api/search/query?product=1&entity-types=page,marriage,obituary&start=*&count=100&keyword={kw}&facet-year=1000&facet-country=200&facet-region=300&facet-county=0&facet-city=0&facet-entity=5&facet-publication=5&include-publication-metadata=true'

    if st_date and end_date:
        st_date = str(st_date)
        end_date = str(end_date)
    
        to_add = f'&date-start={st_date}&date-end={end_date}&facet-year=1000'
        url = url.replace('&facet-year=1000', to_add)

    if state_two_letters:
        state_two_letters = state_two_letters.lower()
        to_add = f'&region=us-{state_two_letters}&keyword='
        url = url.replace('&keyword=', to_add)

    if county:
        county = county.lower()
        to_add = f'&county={county}&region=us'
        url = url.replace('&region=us', to_add)

    return url

url = inputs('race suicide')

class NewsSpider(scrapy.Spider):
    name = 'news'
    #allowed_domains = ['newspapers.com']
    start_urls = [url]
    page_number = 2
    def parse(self, response):

        for start_url in self.start_urls:
            kw_for_next_level = start_url.split('&keyword=')[1].split('&')[0].replace('+','%7C')
            yield Request(start_url,
                          callback=self.parse_records, meta= { 'kw' : kw_for_next_level})

    def parse_records(self, response):
        #'ocr_hit_count'
        data = json.loads(response.text)
        Total_result_number = data['recordCount']

        records = data['records']
        records_dict_list = []
        ids = []
        for record in records:
            r = {}
            r['Title'] = record['publication']['name']
            r['Location'] = record['publication']['location']
            r['Page'] = record['page']['pageNumber']
            r['Date'] = record['page']['date']

            id = str(record['page']['id'])
            url = f'https://www.newspapers.com/image/{id}/?terms=race%20suicide&match=1'
            r['URL'] = url

            ids.append(id)
            records_dict_list.append(r)


        kw = response.meta['kw']
        for i,id in enumerate(ids):
            payload = f'%7B%22id%22:%22{id}%22,%22type%22:%22Image%22%7D'
            of_matches_url = 'https://www.newspapers.com/api/frontend/v1.0/search/aj_getsearchrecord?records=[' + payload + f']&highlight_terms={kw}&checkExtra=true&nonKeywordView=false'
            yield Request(of_matches_url,
                          callback=self.parse_notes,
                            meta = {"Total_result_number" : Total_result_number,
                                     "record": records_dict_list[i]})

        

    def parse_notes(self, response):       
        record = response.meta['record']
        t = response.meta["Total_result_number"]

        res = response.text
        
        matches = res.split('"ocr_hit_count":')[1].split('}')[0]

        record['Note'] = f'1 of {matches} matches'
        yield {
                'total': t,
                'record': record,
            }

        
           
        

    