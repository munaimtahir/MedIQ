package rank

import (
	"sort"
)

// Item is (user_id, percent). Tie-break by user_id for determinism.
type Item struct {
	UserID  string
	Percent float64
}

// Result is (user_id, rank, percentile). Rank 1 is best.
type Result struct {
	UserID     string
	Rank       int
	Percentile float64
}

// RankByPercent sorts by percent desc, tie-break by user_id asc (stable).
// percentile = 100 * (1 - (rank-1)/(n-1)) for n>1 else 100.
func RankByPercent(items []Item) []Result {
	n := len(items)
	if n == 0 {
		return nil
	}

	// Copy and sort: percent desc, then user_id asc
	type kv struct {
		userID  string
		percent float64
	}
	kvs := make([]kv, n)
	for i := range items {
		kvs[i] = kv{items[i].UserID, items[i].Percent}
	}
	sort.Slice(kvs, func(i, j int) bool {
		if kvs[i].percent != kvs[j].percent {
			return kvs[i].percent > kvs[j].percent
		}
		return kvs[i].userID < kvs[j].userID
	})

	out := make([]Result, n)
	for i := range kvs {
		rank := i + 1
		var pct float64
		if n > 1 {
			pct = 100.0 * (1.0 - float64(rank-1)/float64(n-1))
		} else {
			pct = 100.0
		}
		out[i] = Result{
			UserID:     kvs[i].userID,
			Rank:       rank,
			Percentile: pct,
		}
	}
	return out
}
