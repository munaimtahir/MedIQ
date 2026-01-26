package main

import (
	"log"
	"net/http"

	"ranking-go/internal/api"
)

func main() {
	mux := http.NewServeMux()
	api.RegisterHandlers(mux)
	log.Println("ranking-go listening on :8080")
	if err := http.ListenAndServe(":8080", mux); err != nil {
		log.Fatal(err)
	}
}
