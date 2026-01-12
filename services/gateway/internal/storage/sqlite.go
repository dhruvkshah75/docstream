package storage

import (
	"database/sql"
	"log"
	"os"

	_ "github.com/mattn/go-sqlite3" // Import the driver anonymously
)

func InitSQLite() *sql.DB {
	// SQLite stores the database in a file 
	if _, err := os.Stat("./data"); os.IsNotExist(err) {
		os.Mkdir("./data", 0755) // 0755 are linux permissions 
	}

	// opening the connection
	// ./data/auth.db is where the database is stored 
	db, err := sql.Open("sqlite3", "./data/auth.db")
	if err != nil {
		log.Fatalf("Failed to open SQLite database: %v\n", err)
	}

	// Enable Foreign Keys (SQLite defaults to OFF)
	if _, err := db.Exec("PRAGMA foreign_keys = ON;"); err != nil {
		log.Fatal(err)
	}

	// Create the Users Table
	query := `
	CREATE TABLE IF NOT EXISTS users (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		email TEXT NOT NULL UNIQUE,
		password TEXT NOT NULL,
		created_at DATETIME DEFAULT CURRENT_TIMESTAMP
	);`

	if _, err := db.Exec(query); err != nil {
		log.Fatal("Failed to create users table:", err)
	}

	log.Println("Connected to SQLite & Migrated Tables")
	return db
}