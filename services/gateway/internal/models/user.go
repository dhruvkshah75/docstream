package models

import "time"

// `..` these are struct tags so when they are converted to json they are tagged by these 
type User struct {
	ID        int       `json:"id"`
	Email     string    `json:"email"`
	Password  string    `json:"-"` // "-" means never send password in JSON response
	CreatedAt time.Time `json:"created_at"`
}