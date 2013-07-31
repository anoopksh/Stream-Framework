import unittest
from feedly.storage.redis.structures.hash import RedisHashCache,\
    ShardedHashCache
from feedly.storage.redis.structures.list import RedisListCache,\
    FallbackRedisListCache
from feedly.storage.redis.connection import get_redis_connection


class BaseRedisStructureTestCase(unittest.TestCase):

    def get_structure(self):
        return


class RedisSortedSetTest(BaseRedisStructureTestCase):

    def test_zremrangebyrank(self):
        redis = get_redis_connection()
        key = 'test'
        # start out fresh
        redis.delete(key)
        redis.zadd(key, 'a', 1)
        redis.zadd(key, 'b', 2)
        redis.zadd(key, 'c', 3)
        redis.zadd(key, 'd', 4)
        redis.zadd(key, 'e', 5)
        expected_results = [('a', 1.0), ('b', 2.0), ('c', 3.0), (
            'd', 4.0), ('e', 5.0)]
        results = redis.zrange(key, 0, -1, withscores=True)
        self.assertEqual(results, expected_results)
        results = redis.zrange(key, 0, -4, withscores=True)

        # now the idea is to only keep 3,4,5
        max_length = 3
        end = (max_length * -1) - 1
        redis.zremrangebyrank(key, 0, end)
        expected_results = [('c', 3.0), ('d', 4.0), ('e', 5.0)]
        results = redis.zrange(key, 0, -1, withscores=True)
        self.assertEqual(results, expected_results)


class ListCacheTestCase(BaseRedisStructureTestCase):

    def get_structure(self):
        structure_class = type('MyCache', (RedisListCache, ), dict(max_items=10))
        structure = structure_class('test')
        structure.delete()
        return structure

    def test_append(self):
        cache = self.get_structure()
        cache.append_many(['a', 'b'])
        self.assertEqual(cache[:5], ['a', 'b'])
        self.assertEqual(cache.count(), 2)

    def test_simple_append(self):
        cache = self.get_structure()
        for value in ['a', 'b']:
            cache.append(value)
        self.assertEqual(cache[:5], ['a', 'b'])
        self.assertEqual(cache.count(), 2)
        
    def test_trim(self):
        cache = self.get_structure()
        cache.append_many(range(100))
        self.assertEqual(cache.count(), 100)
        cache.trim()
        self.assertEqual(cache.count(), 10)

    def test_remove(self):
        cache = self.get_structure()
        data = ['a', 'b']
        cache.append_many(data)
        self.assertEqual(cache[:5], data)
        self.assertEqual(cache.count(), 2)
        for value in data:
            cache.remove(value)
        self.assertEqual(cache[:5], [])
        self.assertEqual(cache.count(), 0)
        
        
class FakeFallBack(FallbackRedisListCache):
    max_items = 10
    
    def __init__(self, *args, **kwargs):
        self.fallback_data = kwargs.pop('fallback')
        FallbackRedisListCache.__init__(self, *args, **kwargs)
    
    def get_fallback_results(self, start, stop):
        return self.fallback_data[start:stop]
        
        
class FallbackRedisListCacheTest(ListCacheTestCase):
    def get_structure(self):
        structure = FakeFallBack('test', fallback=['a', 'b'])
        structure.delete()
        return structure
    
    def test_remove(self):
        cache = self.get_structure()
        data = ['a', 'b']
        cache.append_many(data)
        self.assertEqual(cache[:5], data)
        self.assertEqual(cache.count(), 2)
        for value in data:
            cache.remove(value)
        self.assertEqual(cache.count(), 0)
        # fallback should still work
        self.assertEqual(cache[:5], data)


class SecondFallbackRedisListCacheTest(BaseRedisStructureTestCase):
    def get_structure(self):
        structure = FakeFallBack('test', fallback=['a', 'b', 'c'])
        structure.delete()
        return structure
    
    def test_append(self):
        cache = self.get_structure()
        # test while we have no redis data
        self.assertEqual(cache[:5], ['a', 'b', 'c'])
        # now test with redis data
        cache.append_many(['d', 'e', 'f', 'g'])
        self.assertEqual(cache.count(), 7)
        self.assertEqual(cache[:3], ['a', 'b', 'c'])

    def test_slice(self):
        cache = self.get_structure()
        # test while we have no redis data
        self.assertEqual(cache[:], ['a', 'b', 'c'])

    
class HashCacheTestCase(BaseRedisStructureTestCase):
    def get_structure(self):
        structure = RedisHashCache('test')
        # always start fresh
        structure.delete()
        return structure

    def test_set_many(self):
        cache = self.get_structure()
        key_value_pairs = [('key', 'value'), ('key2', 'value2')]
        cache.set_many(key_value_pairs)

    def test_get_and_set(self):
        cache = self.get_structure()
        key_value_pairs = [('key', 'value'), ('key2', 'value2')]
        cache.set_many(key_value_pairs)
        results = cache.get_many(['key', 'key2'])
        self.assertEqual(results, {'key2': 'value2', 'key': 'value'})

        result = cache.get('key')
        self.assertEqual(result, 'value')

        result = cache.get('key_missing')
        self.assertEqual(result, None)

    def test_contains(self):
        cache = self.get_structure()
        key_value_pairs = [('key', 'value'), ('key2', 'value2')]
        cache.set_many(key_value_pairs)
        result = cache.contains('key')
        self.assertEqual(result, True)
        result = cache.contains('key2')
        self.assertEqual(result, True)
        result = cache.contains('key_missing')
        self.assertEqual(result, False)

    def test_count(self):
        cache = self.get_structure()
        key_value_pairs = [('key', 'value'), ('key2', 'value2')]
        cache.set_many(key_value_pairs)
        count = cache.count()
        self.assertEqual(count, 2)


class ShardedHashCacheTestCase(BaseRedisStructureTestCase):

    def get_structure(self):
        structure = ShardedHashCache('test')
        # always start fresh
        structure.delete()
        return structure

    def test_set_many(self):
        cache = self.get_structure()
        key_value_pairs = [('key', 'value'), ('key2', 'value2')]
        cache.set_many(key_value_pairs)

    def test_get_and_set(self):
        cache = self.get_structure()
        key_value_pairs = [('key', 'value'), ('key2', 'value2')]
        cache.set_many(key_value_pairs)
        results = cache.get_many(['key', 'key2'])
        self.assertEqual(results, {'key2': 'value2', 'key': 'value'})

        result = cache.get('key')
        self.assertEqual(result, 'value')

        result = cache.get('key_missing')
        self.assertEqual(result, None)

    def test_count(self):
        cache = self.get_structure()
        key_value_pairs = [('key', 'value'), ('key2', 'value2')]
        cache.set_many(key_value_pairs)
        count = cache.count()
        self.assertEqual(count, 2)
