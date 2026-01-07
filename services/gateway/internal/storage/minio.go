package storage

// minio is a Object storage server
import (
	"context"
	"log"
	"os"

	"github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
)

// InitMinio establishes connection to the MinIO Server
func InitMinio() *minio.Client {
	// load the env variables 
	endpoint := os.Getenv("MINIO_ENDPOINT")
	accessKeyID := os.Getenv("MINIO_ACCESS_KEY")
	secretAccessKey := os.Getenv("MINIO_SECRET_KEY")
	useSSL := false 

	minioClient, err := minio.New( endpoint, &minio.Options{
		Creds: credentials.NewStaticV4(accessKeyID, secretAccessKey, ""),
		Secure: useSSL,
	})

	if err != nil {
		// same is Println but it executes os.exit(1)
		log.Fatalln("Failed to connect to the minio server: ", err)
	}

	// check if the Bucket exists if not then we create using helper func
	err = ensureBucketExists(minioClient, "vectormesh-docs")
	if err != nil {
		log.Printf("Warning: Bucket setup failed: %v\n", err);
	}


	log.Println("Successfully connected to MinIO")
	return minioClient
}


// a func to check if bucket exists if not then it creates a new bucket 
func ensureBucketExists(client *minio.Client, bucketName string) error {
	// Used for cancellation / timeouts 
	ctx := context.Background()

	exists, err := client.BucketExists(ctx, bucketName)
	if err != nil {
		return err
	}

	if !exists {
		err := client.MakeBucket(ctx, bucketName, minio.MakeBucketOptions{})
		if err != nil {
			return err
		}
		log.Printf("Created a new bucket: %s\n", bucketName)
	}

	return nil;
}