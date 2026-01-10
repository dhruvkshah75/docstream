package main

import (
	"log"
	"os"
	"time"

	"github.com/dhruvkshah75/vectormesh/gateway/internal/handlers"
	"github.com/dhruvkshah75/vectormesh/gateway/internal/producer"
	"github.com/dhruvkshah75/vectormesh/gateway/internal/storage"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"
)

func main() {
	// We ignore the error if the file is missing because in PRODUCTION, there is no .env file (vars come from Docker/K8s).
	if err := godotenv.Load(); err != nil {
		log.Println("No .env file found!")
	}

	// connect to the minIO service
	minioClient := storage.InitMinio()

	// Connect to Queue
	rabbitConn, rabbitChan, rabbitQueue := producer.InitRabbitMQ()

	// Clean up connections when server stops
	defer rabbitConn.Close()
	defer rabbitChan.Close()

	r := gin.Default()

	// This tells the browser: "It's okay for a frontend running on port 3000 to talk to me"
	r.Use(cors.New(cors.Config{
		AllowOrigins:     []string{"http://localhost:3000"}, // React/Next.js app for frontend
		AllowMethods:     []string{"POST", "GET", "OPTIONS", "PUT", "DELETE"},
		AllowHeaders:     []string{"Origin", "Content-Type", "Authorization"},
		ExposeHeaders:    []string{"Content-Length"},
		AllowCredentials: true,
		MaxAge:           12 * time.Hour,
	}))

	// Register Routes
	// Dependency Injection: Pass the client and channel to the handler
	r.POST("/upload", handlers.UploadHandler(minioClient, rabbitChan, rabbitQueue))
	
	// Simple Health Check
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