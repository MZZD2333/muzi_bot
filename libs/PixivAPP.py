'''
# PixivAPP
* 参考了 https://github.com/upbit/pixivpy
'''
import asyncio
import hashlib
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Literal, TypeAlias

import aiofiles
from httpx import AsyncClient, Limits


_TYPE:      TypeAlias = Literal['illust', 'manga']
_MODE:      TypeAlias = Literal['day', 'day_r18', 'day_male', 'day_female', 'week', 'week_r18', 'week_original', 'week_rookie', 'month']
_SORT:      TypeAlias = Literal['date_desc', 'date_asc', 'popular_desc']
_TARGET:    TypeAlias = Literal['partial_match_for_tags', 'exact_match_for_tags', 'title_and_caption']
_DURATION:  TypeAlias = Literal['within_last_day', 'within_last_week', 'within_last_month']
_RESTRICT:  TypeAlias = Literal['public', 'private']


class PixivClient(AsyncClient):
    class API(Enum):
        auth_hosts = 'https://oauth.secure.pixiv.net/auth/token'
        '''* 登录'''
        search_illust = 'https://app-api.pixiv.net/v1/search/illust'
        '''* 搜索插画'''
        illust_comments = 'https://app-api.pixiv.net/v1/illust/comments'
        '''* 作品评论'''
        illust_detail = 'https://app-api.pixiv.net/v1/illust/detail'
        '''* 插画信息'''
        illust_new = 'https://app-api.pixiv.net/v1/illust/new'
        '''* 大家的新作'''
        illust_ranking = 'https://app-api.pixiv.net/v1/illust/ranking'
        '''* 排行榜'''
        illust_recommended = 'https://app-api.pixiv.net/v1/illust/recommended'
        '''* 推荐作品'''
        illust_recommended_nologin = 'https://app-api.pixiv.net/v1/illust/recommended-nologin'
        '''* 推荐作品 (未登录)'''
        illust_related = 'https://app-api.pixiv.net/v2/illust/related'
        '''* 相关作品'''
        trending_tags_illust = 'https://app-api.pixiv.net/v1/trending-tags/illust'
        '''* 趋势标签'''
        search_user = 'https://app-api.pixiv.net/v1/search/user'
        '''* 搜索用户'''
        user_bookmarks_illust = 'https://app-api.pixiv.net/v1/user/bookmarks/illust'
        '''* 用户收藏作品列表'''
        user_bookmark_tags_illust = 'https://app-api.pixiv.net/v1/user/bookmark-tags/illust'
        '''* 用户收藏标签列表'''
        user_illusts = 'https://app-api.pixiv.net/v1/user/illusts'
        '''* 用户作品列表'''
        user_related = 'https://app-api.pixiv.net/v1/user/related'
        '''* 相关用户'''

    client_id = 'MOBrBDS8blbauoSck0ZfDbtuzpyT'
    client_secret = 'lsACyCD94FhDUtGTXi3QzcFE2uU1hqtDaKeqrdwj'
    hash_secret = '28c1fdd170a5204386cb1313c7077b34f83e4aaf4aa829ce78c231e05b0bae2c'
    

    def __init__(self, timeout: int = 60) -> None:
        headers = {
            'App-OS-Version': '9.3.3',
            'App-OS': 'ios',
            'User-Agent': 'PixivIOSApp/7.13.3 (iOS 14.6; iPhone13,2)',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6'
        }
        super().__init__(headers=headers, timeout=timeout, verify=False,
            limits=Limits(max_keepalive_connections=30, max_connections=150))    
    

class PixivApp(PixivClient):
    class User:
        id: str = ''
        name: str = ''
        account: str = ''
        is_premium: bool = False
        profile_image_urls: dict = {}

    refresh_token: str = ''
    access_token: str = ''
    login_in = False
    download_proxy = ''

    def set_download_proxy(self, proxy: str = ''):
        '''
        # 设置下载代理
        * 例如 `i.pixiv.re`
        '''
        self.download_proxy = proxy

    async def _download(self, url: str, save_path: Path|str = './', file_name: str = '', timeout: int = 20) -> int:
        if self.download_proxy:
            url = url.replace('i.pximg.net', self.download_proxy)
        headers = self.headers.copy()
        headers['Referer'] = 'https://app-api.pixiv.net/'
        file_name = file_name if file_name else url.split('/')[-1]
        path = Path(save_path) / file_name
        try:
            async with self.stream(method='GET', url=url, headers=headers, timeout=timeout) as resp:
                if resp.status_code == 200:
                    async with aiofiles.open(path, 'wb') as file:
                        async for chunck in resp.aiter_bytes(chunk_size=64):
                            await file.write(chunck)
                    file_size = int(resp.headers['Content-Length'])
                    return file_size
                else:
                    return 0
        except:
            return 0
    
    async def download(self, task_info: list[tuple[str, Path|str, str]], timeout: int = 20) -> list[int]:
        task = [asyncio.create_task(self._download(url=url, save_path=save_path, file_name=file_name, timeout=timeout)) for url, save_path, file_name in task_info]
        return await asyncio.gather(*task)

    async def __auto_relogin(self):
        await asyncio.sleep(3600)
        await self.login(self.refresh_token)

    async def login(self, 
        refresh_token) -> bool:
        '''
        ## 登录 
        * 仅能使用 `refresh_token` 进行登录
        '''
        data = {
            'get_secure_url': 1,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'hash_secret': self.hash_secret,
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
        }
        headers = self.headers.copy()
        local_time = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S+00:00')
        headers['X-Client-Time'] = local_time
        headers['X-Client-Hash'] = hashlib.md5((local_time + self.hash_secret).encode('utf-8')).hexdigest()
        resp = await self.post(url=self.API.auth_hosts.value, headers=headers, data=data)
        
        if resp.status_code != 200:
            return False
        resp_data: dict = resp.json()
        if resp_data.get('access_token', ''):
            self.access_token = resp_data.get('access_token', '')
            self.refresh_token = resp_data.get('refresh_token', '')
            self.login_in = True
            user_data = resp_data.get('user', {})
            self.User.id = user_data.get('id', '')
            self.User.name = user_data.get('name', '')
            self.User.account = user_data.get('account', '')
            self.User.is_premium = user_data.get('is_premium', False)
            self.User.profile_image_urls = user_data.get('profile_image_urls', {})
            self.headers['Authorization'] = 'Bearer '+self.access_token
            asyncio.run_coroutine_threadsafe(self.__auto_relogin(), asyncio.get_running_loop())
            return True
        return False

    async def search_illust(self,
        word: str,
        search_target: _TARGET = 'partial_match_for_tags',
        sort: _SORT = 'date_desc',
        duration: _DURATION|None = None,
        offset: int = 0,
        start_date: str|None = None,
        end_date: str|None = None,
        timeout: int = 30) -> dict:
        '''
        ## 搜索插画 `需登录`
        * word                        关键字 | `eg`: 初音未来
        * search_target             搜索条件 | `partial_match_for_tags`: 标签部分一致, `exact_match_for_tags`: 标签完全一致, `title_and_caption`: 标题说明文
        * sort                      排序方式 | `date_desc`: 降序, `date_asc`: 升序, `popular_desc`: 热门排序
        * duration                  时间限定 | `within_last_day`: 一天内, `within_last_week`: 一周内, `within_last_month`: 一月内
        * start_date                起始日期 | `eg`: 2022-02-22
        * end_date                  截止日期 | `eg`: 2022-02-23
        * offset                    起始位置 | `eg`: 0
        '''
        params = {
            'word': word,
            'filter': 'for_ios',
            'search_target': search_target,
            'sort': sort,
            'duration': duration,
            'offset': offset,
            'start_date': start_date,
            'end_date': end_date
        }
        resp = await self.get(url=self.API.search_illust.value, headers=self.headers, params=params, timeout=timeout)
        return resp.json()

    async def illust_comments(self, 
        illust_id: int | str,
        include_total_comments = True,
        offset: int = 0,
        timeout: int = 30) -> dict:
        '''
        ## 插画评论 `需登录`
        * illust_id                   插画ID | `eg`: 12345678
        * include_total_comments包括全部评论 |  `eg`: True
        * offset                    起始位置 | `eg`: 0
        '''
        params = {
            'illust_id': illust_id,
            'include_total_comments': include_total_comments,
            'offset': offset,
        }
        resp = await self.get(url=self.API.illust_comments.value, params=params, timeout = timeout)
        return resp.json()

    async def illust_detail(self, 
        illust_id: int | str, 
        timeout: int = 30) -> dict:
        '''
        ## 插画信息 `需登录`
        * illust_id                   插画ID | `eg`: 12345678
        '''
        params = {
            'illust_id': illust_id,
        }
        resp = await self.get(url=self.API.illust_detail.value, params=params, timeout = timeout)
        return resp.json()

    async def illust_new(self,
        content_type: _TYPE = 'illust', 
        max_illust_id: int|None= None,
        timeout: int = 30) -> dict:
        '''
        ## 大家的新作 `需登录`
        * content_type              作品类型 | `illust`: 插画, `manga`: 漫画
        * max_illust_id           最大作品ID | `eg`: 100000000
        '''
        params = {
            'content_type': content_type,
            'filter': 'for_ios',
        }
        if max_illust_id:
            params['max_illust_id'] = max_illust_id
        resp = await self.get(self.API.illust_new.value, headers=self.headers, params=params, timeout=timeout)
        return resp.json()

    async def illust_ranking(self, 
        mode: _MODE = 'day', 
        date: str = '', 
        offset: int = 0, 
        timeout: int = 30) -> dict:
        '''
        ## 排行榜 `需登录`      
        * mode                    排行榜类型 | `day`: 每日, `day_male`: 男性向, `day_female`: 女性向, `week`: 每周, `week_original`: 原创, `week_rookie`: 新人, `month`: 每月, `day_r18`: 每日 R-18, `week_r18`: 每周 R-18
        * date                          日期 | `eg`: 2022-02-22
        * offset                    起始位置 | `eg`: 0
        '''
        params = {
            'mode': mode,
            'filter': 'for_ios',
            'date': date,
            'offset': offset,
        }
        resp = await self.get(url=self.API.illust_ranking.value, headers=self.headers, params=params, timeout=timeout)
        return resp.json()

    async def illust_recommended(self, 
        content_type: _TYPE = 'illust', 
        include_ranking_label: bool = True, 
        offset: int = 0,
        max_bookmark_id_for_recommend: int|None= None, 
        min_bookmark_id_for_recent_illust: int|None= None, 
        viewed: list |None= None,
        include_ranking_illusts=None, 
        bookmark_illust_ids: list |None= None, 
        include_privacy_policy=None, 
        timeout: int = 30) -> dict:
        '''
        ## 推荐作品
        * content_type                          作品类型 | `illust`: 插画, `manga`: 漫画
        * include_ranking_label           包括排行榜标签 | 
        * include_ranking_illusts         包括排行榜插画 | 
        * max_bookmark_id_for_recommend 推荐作品的最大ID | 
        * min_bookmark_id_for_recommend 推荐作品的最大ID | 
        * offset                                起始位置 | `eg`: 0
        '''
        params = {
            'content_type': content_type,
            'offset': offset,
            'filter': 'for_ios',
        }
        if viewed:
            params['viewed'] = viewed
        if bookmark_illust_ids:
            params['bookmark_illust_ids'] = bookmark_illust_ids
        if include_ranking_illusts:
            params['include_ranking_illusts'] = include_ranking_illusts
        if include_ranking_label:
            params['include_ranking_label'] = include_ranking_label
        if include_privacy_policy:
            params['include_privacy_policy'] = include_privacy_policy
        if max_bookmark_id_for_recommend:
            params['max_bookmark_id_for_recommend'] = max_bookmark_id_for_recommend
        if min_bookmark_id_for_recent_illust:
            params['min_bookmark_id_for_recent_illust'] = min_bookmark_id_for_recent_illust
            
        url = self.API.illust_recommended.value if self.login_in else self.API.illust_recommended_nologin.value
        resp = await self.get(url=url, headers=self.headers, params=params, timeout=timeout)
        return resp.json()

    async def illust_related(self, 
        illust_id: int | str, 
        offset: int = 0,
        timeout: int = 30) -> dict:
        '''
        ## 相关作品 `需登录`
        * illust_id                   插画ID | `eg`: 12345678
        * offset                    起始位置 | `eg`: 0
        '''
        params = {
            'illust_id': illust_id,
            'filter': 'for_ios',
            'offset': offset,
        }
        resp = await self.get(url=self.API.illust_related.value, headers=self.headers, params=params, timeout=timeout)
        return resp.json()

    async def trending_tags_illust(self, 
        timeout: int = 30) -> dict:
        '''
        ## 趋势标签 `需登录`
        '''
        params = {
            'filter': 'for_ios',
        }
        resp = await self.get(url=self.API.trending_tags_illust.value, headers=self.headers, params=params, timeout=timeout)
        return resp.json()

    async def search_user(self,
        word: str,
        sort: _SORT = 'date_desc',
        duration: _DURATION|None = None,
        offset: int = 0,
        timeout: int = 30) -> dict:
        '''
        ## 搜索用户 `需登录`
        * word                        关键字 | `eg`: username
        * sort                      排序方式 | `date_desc`: 降序, `date_asc`: 升序, `popular_desc`: 热门排序
        * duration                  时间限定 | `within_last_day`: 一天内, `within_last_week`: 一周内, `within_last_month`: 一月内
        * offset                    起始位置 | `eg`: 0
        '''
        params = {
            'word': word,
            'filter': 'for_ios',
            'sort': sort,
            'duration': duration,
            'offset': offset,
        }
        resp = await self.get(url=self.API.search_user.value, headers=self.headers, params=params, timeout=timeout)
        return resp.json()

    async def user_bookmarks_illust(self,
        user_id: int ,
        restrict: _RESTRICT = 'public',
        max_bookmark_id: int|None= None,
        tag: str|None = None,
        offset: int = 0,
        timeout: int = 30) -> dict:
        '''
        ## 用户收藏作品 `需登录`
        * user_id                     用户ID | `eg`: 1234567
        * restrict                  限制类型 | `public`: 公开, `private`: 私人
        * max_bookmark_id     最大收藏作品ID | `eg`: 100000000
        * tag                       收藏标签 | 
        * offset                    起始位置 | `eg`: 0
        '''
        params = {
            'user_id': user_id,
            'filter': 'for_ios',
            'restrict': restrict,
            'offset': offset,
        }
        if max_bookmark_id:
            params['max_bookmark_id'] = max_bookmark_id
        if tag:
            params['tag'] = tag
        resp = await self.get(url=self.API.user_bookmarks_illust.value, headers=self.headers, params=params, timeout=timeout)
        return resp.json()

    async def user_bookmark_tags_illust(self,
        user_id: int|None= None,
        restrict: _RESTRICT = 'public',
        offset: int = 0,
        timeout: int = 30) -> dict:
        '''
        ## 用户收藏标签 `需登录`
        * user_id                     用户ID | `eg`: 1234567
        * restrict                  限制类型 | `public`: 公开, `private`: 私人
        * offset                    起始位置 | `eg`: 0
        '''
        params = {
            'filter': 'for_ios',
            'restrict': restrict,
            'offset': offset,
        }
        if user_id:
            params['user_id'] = user_id
        resp = await self.get(url=self.API.user_bookmark_tags_illust.value, headers=self.headers, params=params, timeout=timeout)
        return resp.json()

    async def user_illusts(self, 
        user_id: int, 
        type: _TYPE = 'illust', 
        offset: int = 0, 
        timeout: int = 30) -> dict:
        '''
        ## 用户作品 `需登录`
        * user_id                    用户ID  | `eg`: 1234567
        * type                      作品类型 | `illust`: 插画, `manga`: 漫画
        * offset                    起始位置 | `eg`: 0
        '''
        params = {
            'user_id': user_id,
            'filter': 'for_ios',
            'type': type,
            'offset': offset
        }
        resp = await self.get(url=self.API.user_illusts.value, headers=self.headers, params=params, timeout=timeout)
        return resp.json()

    async def user_related(self, 
        seed_user_id: int, 
        offset: int = 0, 
        timeout: int = 30) -> dict:
        '''
        ## 相关用户 `需登录`
        * seed_user_id                用户ID | `eg`: 1234567
        * offset                    起始位置 | `eg`: 0
        '''
        params = {
            'seed_user_id': seed_user_id,
            'filter': 'for_ios',
            'offset': offset
        }
        resp = await self.get(url=self.API.user_related.value, headers=self.headers, params=params, timeout=timeout)
        return resp.json()



PIXIVAPP = PixivApp()