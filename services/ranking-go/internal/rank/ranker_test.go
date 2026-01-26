package rank

import (
	"reflect"
	"testing"
)

func TestRankByPercentDeterministic(t *testing.T) {
	// Same input multiple times -> same output
	items := []Item{
		{UserID: "a", Percent: 80},
		{UserID: "b", Percent: 90},
		{UserID: "c", Percent: 80},
	}
	r1 := RankByPercent(items)
	r2 := RankByPercent(items)
	if !reflect.DeepEqual(r1, r2) {
		t.Fatalf("determinism violated: %v vs %v", r1, r2)
	}
	// 90 first, then 80,80 tie-break by user_id
	if r1[0].UserID != "b" || r1[0].Rank != 1 || r1[0].Percentile != 100 {
		t.Errorf("expected rank 1 = b, 100: got %+v", r1[0])
	}
	if r1[1].Rank != 2 || r1[2].Rank != 3 {
		t.Errorf("expected ranks 2,3: got %d %d", r1[1].Rank, r1[2].Rank)
	}
}

func TestRankByPercentSingle(t *testing.T) {
	r := RankByPercent([]Item{{UserID: "x", Percent: 50}})
	if len(r) != 1 || r[0].Rank != 1 || r[0].Percentile != 100 {
		t.Fatalf("single user: got %+v", r)
	}
}

func TestRankByPercentEmpty(t *testing.T) {
	r := RankByPercent(nil)
	if r != nil {
		t.Fatalf("expected nil: got %v", r)
	}
	r = RankByPercent([]Item{})
	if r != nil {
		t.Fatalf("expected nil: got %v", r)
	}
}
