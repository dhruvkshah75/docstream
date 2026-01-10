package handlers

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"time"

	"github.com/dhruvkshah75/vectormesh/gateway/internal/producer"
	"github.com/gin-gonic/gin"
	"github.com/minio/minio-go/v7"
	amqp "github.com/rabbitmq/amqp091-go"
)



func UploadHandler(minioClient *minio.Client, ch *amqp.Channel, q amqp.Queue) gin.HandlerFunc {
	// gin.HandlerFunc handles HTTP request
	return func(c *gin.Context) {
		// check if the file exists or not in request 
		file, err := c.FormFile("file")
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "No file uploaded"})
			return;
		}

		// Open the file stream
		src, err := file.Open()
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Unable to open file"})
		}
		defer src.Close()

		// Upload to MinIO which is Object Storage Server 
		// Create a unique filename: timestamp_originalName.pdf
		fileName := fmt.Sprintf("%d_%s", time.Now().Unix(), filepath.Base(file.Filename))
		bucketName := os.Getenv("MINIO_BUCKET_NAME")

		// Stream directly to MinIO (effiecient for large files)
		info, err := minioClient.PutObject(context.Background(), bucketName, fileName, src, file.Size, minio.PutObjectOptions{
				ContentType: "application/pdf",
		})
		if err != nil {
			log.Println("MinIO Upload Error:", err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to upload to MinIO storage server"})
			return
		}

		// Create Job Payload 
		// This is the "Ticket" we send to the Worker
		jobPayload := map[string]interface{}{
			"job_id": fmt.Sprintf("job_%d", time.Now().Unix()),
			"filename": fileName,
			"bucket": bucketName,
			"file_size": info.Size,
			"status": "pending",
			"timestamp": time.Now().Unix(),
		}

		body, _ := json.Marshal(jobPayload)

		// Publish to RabbitMQ using the helper func made 
		err = producer.PublishJob(ch, q, body)
		if err != nil {
			log.Println("Queue Error: ", err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to queue job"})
			return
		}

		// Success response 
		c.JSON(http.StatusOK, gin.H{
			"message": "File uploaded and processing started",
			"job_id":  jobPayload["job_id"],
			"file_id": info.Key,
		})

	}
}
