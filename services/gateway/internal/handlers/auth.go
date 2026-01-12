package handlers

import (
	"database/sql"
	"net/http"
	"os"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/golang-jwt/jwt/v5"
	"golang.org/x/crypto/bcrypt"
)

type AuthHandler struct {
	DB *sql.DB
}

// Constructor to create a DB connection 
func NewAuthHandler(db *sql.DB) *AuthHandler {
	return &AuthHandler{DB: db}
}

type AuthInput struct {
	Email    string `json:"email" binding:"required"`
	Password string `json:"password" binding:"required"`
}

// --- SIGNUP ---
func (h *AuthHandler) Signup(c *gin.Context) {
	var input AuthInput
	if err := c.ShouldBindJSON(&input); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Hash the password (Never store plain text!)
	hashedPassword, err := bcrypt.GenerateFromPassword([]byte(input.Password), bcrypt.DefaultCost)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to hash password"})
		return
	}

	// Insert into DB
	query := `INSERT INTO users (email, password) VALUES (?, ?)`
	_, err = h.DB.Exec(query, input.Email, string(hashedPassword))
	
	if err != nil {
		// This likely means the email already exists (UNIQUE constraint)
		c.JSON(http.StatusBadRequest, gin.H{"error": "User already exists"})
		return
	}

	c.JSON(http.StatusCreated, gin.H{"message": "User created successfully"})
}

// --- LOGIN ---
func (h *AuthHandler) Login(c *gin.Context) {
	var input AuthInput
	if err := c.ShouldBindJSON(&input); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Find user by email
	var storedHash string
	var userID int
	
	query := `SELECT id, password FROM users WHERE email = ?`
	err := h.DB.QueryRow(query, input.Email).Scan(&userID, &storedHash)

	if err == sql.ErrNoRows {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Invalid email or password"})
		return
	} else if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Database error"})
		return
	}

	// Compare the provided password with the stored hash
	if err := bcrypt.CompareHashAndPassword([]byte(storedHash), []byte(input.Password)); err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Invalid email or password"})
		return
	}

	// Generate JWT Token
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"sub": userID,
		"exp": time.Now().Add(time.Hour * 24 * 7).Unix(), // 7 days
	})

	// Sign the token with a secret key
	secret := os.Getenv("JWT_SECRET")
	if secret == "" {
		secret = "default_secret_dont_use_in_prod" 
	}
	
	tokenString, err := token.SignedString([]byte(secret))
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to generate token"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"token": tokenString})
}