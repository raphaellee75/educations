import json
import os
import pandas
import pyperclip
import selenium
import sys
import time

from bs4 import *


# 공통 로그 함수
def line_logging(*messages):
    import datetime
    log_time = datetime.datetime.today().strftime('[%Y/%m/%d %H:%M:%S]')
    log = list()
    for message in messages:
        log.append(str(message))
    print(log_time + ':[' + ' '.join(log) + ']', flush=True)


# crawling function
def get_post(p_url, p_param, p_sleep_time=2, p_flag_view_url=True):
    import time
    import urllib
    import requests

    url_full_path = p_url + '?' + urllib.parse.urlencode(p_param)
    if p_flag_view_url:
        line_logging(url_full_path)
    headers = {
        'content-type': 'application/json, text/javascript, */*; q=0.01',
        'User-Agent': 'Mozilla/5.0 AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.0 Safari/605.1.15',
        'referer': 'http://finance.daum.net/domestic/exchange/COMMODITY-%2FCLc1'
    }
    try:
        results = requests.get(url_full_path, headers=headers)
        time.sleep(p_sleep_time)
        return results
    except:
        time.sleep(p_sleep_time * 2)
        results = requests.get(url_full_path, headers=headers)
        time.sleep(p_sleep_time)
        return results


# ====================================================================================================================================================================================================
# HTML Parsing
# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# 국내 지수 (코스피/코스닥) 수집
# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
def collect_korea(p_market, page_no=1, p_sleep_time=2):
    url = "https://finance.naver.com/sise/sise_index_day.nhn"

    list_price = list()
    param = {
        'code': p_market,
        'page': page_no
    }
    results = get_post(url, param, p_sleep_time=p_sleep_time)
    price_table = BeautifulSoup(results.content, "html.parser").find_all('table')[0]
    price_trs = BeautifulSoup(str(price_table), "html.parser").find_all('tr')
    for price_tr in price_trs:
        row = BeautifulSoup(str(price_tr), "html.parser").find_all('td')
        if len(row) > 3:
            list_price.append({
                'eod_date': int(row[0].text.strip().replace('.', '')),
                'item_code': p_market,
                'price_close': float(row[1].text.strip().replace(',', '')),
                'trade_amount': int(row[4].text.strip().replace(',', '')),
                'diff': float(row[2].text.strip().replace(',', '')),
                'rate': float(row[3].text.strip().replace(',', '').replace('%', '').replace('+', '')),
            })
    return pandas.DataFrame(list_price)


# 국내 지수 (코스피/코스닥) 수집 결과 저장
def save_kospi_and_kosdaq(p_market, page_to=10):
    page_from = 1
    df_index = pandas.DataFrame()
    count_of_date = 0

    for page_no in range(page_from, page_to):
        df_page = collect_korea(p_market, page_no=page_no)
        if df_index.shape[0] > 0:
            df = df_index[~df_index['eod_date'].isin(set(df_page['eod_date'].unique()))]
        else:
            df = df_index
        df_index = pandas.concat([df, df_page], sort=False)
        df_index = df_index.drop_duplicates()
        df_index = df_index.set_index(['eod_date'])
        df_index = df_index.sort_index(ascending=False)
        df_index = df_index.reset_index()

        line_logging('save_kospi_and_kosdaq', p_market, 'Start:', df_index.tail(1)['eod_date'].tolist()[0], ',Finish:', df_index.head(1)['eod_date'].tolist()[0], count_of_date, df_index.shape)
        if count_of_date == df_index.shape[0]:
            break
        count_of_date = df_index.shape[0]
    
    return df_index
# ====================================================================================================================================================================================================

# ====================================================================================================================================================================================================
# JSON loading
# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# 한국은행 데이터 수집 함수
# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
def get_ECOS_MM(p_flag):
    import urllib
    import urllib.request
    import urllib.parse
    import json

    base_url = 'https://ecos.bok.or.kr/jsp/vis/keystat/Key100Stat_n1.jsp'

    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Host': 'ecos.bok.or.kr',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://ecos.bok.or.kr/jsp/vis/keystat/',
        'Connection': 'keep-alive',
    }

    # 파라미터 세팅
    params = '?' + urllib.parse.urlencode({
        urllib.parse.quote_plus('languageFlg'): 'MM',
        urllib.parse.quote_plus('languageFlg2'): '1',
        urllib.parse.quote_plus('languageFlg3'): p_flag,
        urllib.parse.quote_plus('languageFlg4'): '%20',
        urllib.parse.quote_plus('languageFlg5'): 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15',
    })
    req = urllib.request.Request(base_url + urllib.parse.unquote(params), headers=headers)
    response_body = urllib.request.urlopen(req).read()
    json_data = json.loads(response_body)[0]

    list_row = list()
    for item_info in json_data:
        yyyymm = int(item_info['TIME'])
        if yyyymm < 201401:
            continue
        list_row.append({
            'yyyymm': yyyymm,
            'item_code': p_flag,
            'value': item_info['DATA_VALUE'],
        })

    time.sleep(1.5)
    return pandas.DataFrame(list_row)
# ====================================================================================================================================================================================================

# ====================================================================================================================================================================================================
# Selenium
# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# 클립보드에 input을 복사한 뒤, 해당 내용을 actionChain을 이용해 로그인 폼에 붙여넣기
# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
def copy_input(p_driver, xpath, input):
    pyperclip.copy(input)
    p_driver.find_element_by_xpath(xpath).click()
    selenium.webdriver.common.action_chains.ActionChains(p_driver).\
        key_down(selenium.webdriver.common.keys.Keys.COMMAND).send_keys('v').\
        key_up(selenium.webdriver.common.keys.Keys.COMMAND).perform()
# ====================================================================================================================================================================================================

# ====================================================================================================================================================================================================
# API
# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
def get_ASOS(p_api_key, p_start_date, p_finish_date, stn_id, p_page_number=1):
    line_logging('get_ASOS is started.', p_start_date, p_finish_date, stn_id, p_page_number)
    import urllib
    import urllib.request
    import urllib.parse
    import json

    url = 'http://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList'
    # parameter for request
    params = '?' + urllib.parse.urlencode({
        urllib.parse.quote_plus('serviceKey'): p_api_key,
        urllib.parse.quote_plus('numOfRows'): '10',
        urllib.parse.quote_plus('pageNo'): p_page_number,
        urllib.parse.quote_plus('dataType'): 'json',
        urllib.parse.quote_plus('dataCd'): 'ASOS',
        urllib.parse.quote_plus('dateCd'): 'DAY',
        urllib.parse.quote_plus('startDt'): p_start_date,
        urllib.parse.quote_plus('endDt'): p_finish_date,
        urllib.parse.quote_plus('stnIds'): stn_id,
    })
    req = urllib.request.Request(url + urllib.parse.unquote(params))
    response_body = urllib.request.urlopen(req).read()
    json_data = json.loads(response_body)

    json_info = json_data['response']['body']
    list_items = json_info['items']['item']
    list_row = list()
    for item_info in list_items:
        list_row.append({
            'COL-01': str(item_info['stnId']),
            'COL-02': str(item_info['stnNm']),
            'COL-03': str(item_info['tm']),
            'COL-04': str(item_info['avgTa']),
            'COL-05': str(item_info['minTa']),
            'COL-06': str(item_info['minTaHrmt']),
            'COL-07': str(item_info['maxTa']),
            'COL-08': str(item_info['maxTaHrmt']),
            'COL-09': str(item_info['sumRnDur']),
            'COL-10': str(item_info['mi10MaxRn']),
            'COL-11': str(item_info['mi10MaxRnHrmt']),
            'COL-12': str(item_info['hr1MaxRn']),
            'COL-13': str(item_info['hr1MaxRnHrmt']),
            'COL-14': str(item_info['sumRn']),
            'COL-15': str(item_info['maxInsWs']),
            'COL-16': str(item_info['maxInsWsWd']),
            'COL-17': str(item_info['maxInsWsHrmt']),
            'COL-18': str(item_info['maxWs']),
            'COL-19': str(item_info['maxWsWd']),
            'COL-20': str(item_info['maxWsHrmt']),
            'COL-21': str(item_info['avgWs']),
            'COL-22': str(item_info['hr24SumRws']),
            'COL-23': str(item_info['maxWd']),
            'COL-24': str(item_info['avgTd']),
            'COL-25': str(item_info['minRhm']),
            'COL-26': str(item_info['minRhmHrmt']),
            'COL-27': str(item_info['avgRhm']),
            'COL-28': str(item_info['avgPv']),
            'COL-29': str(item_info['avgPa']),
            'COL-30': str(item_info['maxPs']),
            'COL-31': str(item_info['maxPsHrmt']),
            'COL-32': str(item_info['minPs']),
            'COL-33': str(item_info['minPsHrmt']),
            'COL-34': str(item_info['avgPs']),
            'COL-35': str(item_info['ssDur']),
            'COL-36': str(item_info['sumSsHr']),
            'COL-37': str(item_info['hr1MaxIcsrHrmt']),
            'COL-38': str(item_info['hr1MaxIcsr']),
            'COL-39': str(item_info['sumGsr']),
            'COL-40': str(item_info['ddMefs']),
            'COL-41': str(item_info['ddMefsHrmt']),
            'COL-42': str(item_info['ddMes']),
            'COL-43': str(item_info['ddMesHrmt']),
            'COL-44': str(item_info['sumDpthFhsc']),
            'COL-45': str(item_info['avgTca']),
            'COL-46': str(item_info['avgLmac']),
            'COL-47': str(item_info['avgTs']),
            'COL-48': str(item_info['minTg']),
            'COL-49': str(item_info['avgCm5Te']),
            'COL-50': str(item_info['avgCm10Te']),
            'COL-51': str(item_info['avgCm20Te']),
            'COL-52': str(item_info['avgCm30Te']),
            'COL-53': str(item_info['avgM05Te']),
            'COL-54': str(item_info['avgM10Te']),
            'COL-55': str(item_info['avgM15Te']),
            'COL-56': str(item_info['avgM30Te']),
            'COL-57': str(item_info['avgM50Te']),
            'COL-58': str(item_info['sumLrgEv']),
            'COL-59': str(item_info['sumSmlEv']),
            'COL-60': str(item_info['n99Rn']),
            'COL-61': str(item_info['iscs']),
            'COL-62': str(item_info['sumFogDur']),
        })

    line_logging('get_ASOS is finished.', p_start_date, p_finish_date, stn_id, p_page_number)

    time.sleep(1.5)
    return pandas.DataFrame(list_row), json_info['totalCount']