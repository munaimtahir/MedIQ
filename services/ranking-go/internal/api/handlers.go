package api

import (
	"encoding/json"
	"net/http"

	"ranking-go/internal/rank"
)

func RegisterHandlers(mux *http.ServeMux) {
	mux.HandleFunc("GET /health", health)
	mux.HandleFunc("POST /rank", rankHandler)
}

func health(w http.ResponseWriter, _ *http.Request) {
	w.WriteHeader(http.StatusOK)
	w.Write([]byte("ok"))
}

type rankRequest struct {
	CohortID string       `json:"cohort_id"`
	Items    []rankItem   `json:"items"`
}

type rankItem struct {
	UserID  string  `json:"user_id"`
	Percent float64 `json:"percent"`
}

type rankResult struct {
	UserID    string  `json:"user_id"`
	Rank      int     `json:"rank"`
	Percentile float64 `json:"percentile"`
}

type rankResponse struct {
	CohortID string       `json:"cohort_id"`
	Results  []rankResult `json:"results"`
}

func rankHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req rankRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "invalid json: "+err.Error(), http.StatusBadRequest)
		return
	}

	items := make([]rank.Item, len(req.Items))
	for i, it := range req.Items {
		items[i] = rank.Item{UserID: it.UserID, Percent: it.Percent}
	}

	results := rank.RankByPercent(items)

	out := rankResponse{
		CohortID: req.CohortID,
		Results:  make([]rankResult, len(results)),
	}
	for i, r := range results {
		out.Results[i] = rankResult{
			UserID:     r.UserID,
			Rank:       r.Rank,
			Percentile: r.Percentile,
		}
	}

	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(out)
}
