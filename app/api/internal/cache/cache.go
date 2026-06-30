// Package cache wraps Redis for both caching and a simple list-based job queue.
package cache

import (
	"context"
	"time"

	"github.com/redis/go-redis/v9"
)

type Cache struct {
	rdb *redis.Client
}

func New(url string) (*Cache, error) {
	opt, err := redis.ParseURL(url)
	if err != nil {
		return nil, err
	}
	return &Cache{rdb: redis.NewClient(opt)}, nil
}

func (c *Cache) Close() error { return c.rdb.Close() }

func (c *Cache) Ping(ctx context.Context) error { return c.rdb.Ping(ctx).Err() }

func (c *Cache) Get(ctx context.Context, key string) (string, bool, error) {
	v, err := c.rdb.Get(ctx, key).Result()
	if err == redis.Nil {
		return "", false, nil
	}
	if err != nil {
		return "", false, err
	}
	return v, true, nil
}

func (c *Cache) Set(ctx context.Context, key, value string, ttl time.Duration) error {
	return c.rdb.Set(ctx, key, value, ttl).Err()
}

func (c *Cache) Del(ctx context.Context, keys ...string) error {
	return c.rdb.Del(ctx, keys...).Err()
}

// Enqueue pushes a job payload onto a list-based queue.
func (c *Cache) Enqueue(ctx context.Context, queue, payload string) error {
	return c.rdb.LPush(ctx, queue, payload).Err()
}

// Dequeue blocks up to timeout for the next job. Returns ok=false on timeout.
func (c *Cache) Dequeue(ctx context.Context, queue string, timeout time.Duration) (string, bool, error) {
	res, err := c.rdb.BRPop(ctx, timeout, queue).Result()
	if err == redis.Nil {
		return "", false, nil
	}
	if err != nil {
		return "", false, err
	}
	if len(res) != 2 {
		return "", false, nil
	}
	return res[1], true, nil // res = [queue, value]
}
