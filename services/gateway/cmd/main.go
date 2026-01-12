package main

import (
	"log"
	"os"
	"time"

	"github.com/dhruvkshah75/docstream/gateway/internal/handlers"
	"github.com/dhruvkshah75/docstream/gateway/internal/producer"
	"github.com/dhruvkshah75/docstream/gateway/internal/storage"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"
)

func main() {
	// 1. Load Env
	if err := godotenv.Load(); err != nil {
		log.Println("No .env file found, using system vars")
	}

	// 2. Initialize Infrastructure
	minioClient := storage.InitMinio()
	rabbitConn, rabbitChan, rabbitQueue := producer.InitRabbitMQ()
	
	// --- Initialize SQLite ---
	sqliteDB := storage.InitSQLite() // calling the storage.sqlite.go file 

	// close the connections when the server stops 
	defer rabbitConn.Close()
	defer rabbitChan.Close()
	defer sqliteDB.Close() 

	// Initialize Handlers
	authHandler := handlers.NewAuthHandler(sqliteDB) // Create Auth Handler

	r := gin.Default()

	// CORS Config
	r.Use(cors.New(cors.Config{
		AllowOrigins:     []string{"http://localhost:3000"},  // the frontend to talk 
		AllowMethods:     []string{"POST", "GET", "OPTIONS", "PUT", "DELETE"},
		AllowHeaders:     []string{"Origin", "Content-Type", "Authorization"},
		ExposeHeaders:    []string{"Content-Length"},
		AllowCredentials: true,
		MaxAge:           12 * time.Hour,
	}))

	// --- Routes --
	// Auth Routes
	r.POST("/signup", authHandler.Signup) 
	r.POST("/login", authHandler.Login)   

	// Upload Route
	r.POST("/upload", handlers.UploadHandler(minioClient, rabbitChan, rabbitQueue))
	
	// Health Check
	r.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{"status": "Gateway is active"})
	})

	// Start Server
	port := os.Getenv("API_GATEWAY_PORT")
	if port == ""{
		log.Fatalln("port is missing!")
	}
	addr := ":" + port
	log.Println("API Gateway running on port: ", port)
	if err := r.Run(addr); err != nil {
		log.Fatalln("Failed to start server:", err)
	}
}