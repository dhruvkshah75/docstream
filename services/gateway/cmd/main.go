package main

import (
	"log"

	"github.com/joho/godotenv"
)

func main() {
	// We ignore the error if the file is missing because in PRODUCTION, there is no .env file (vars come from Docker/K8s).
	if err := godotenv.Load(); err != nil {
		log.Println("No .env file found!")
	}
}