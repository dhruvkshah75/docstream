package producer

import (
	"log"
	"os"

	amqp "github.com/rabbitmq/amqp091-go"
)

// InitRabbitMQ connects to the RabbitMQ and declares the queue
func InitRabbitMQ() (*amqp.Connection, *amqp.Channel, amqp.Queue){
	url := os.Getenv("RABBITMQ_URL")

	queueName := "ingestion_queue"

	// Connect
	conn, err := amqp.Dial(url)
	if err != nil {
		log.Fatalln("Failed to connect to RabbitMQ: ", err)
	}

	// Open channel
	ch, err := conn.Channel()
	if err != nil {
		log.Fatalln("Failed to open RabbitMQ channel: ", err)
	}

	// Declare Queue 
	q, err := ch.QueueDeclare(
		queueName, // name
		true,      // durable
		false,     // delete when unused
		false,     // exclusive
		false,     // no-wait
		nil,       // arguments
	)
	if err != nil {
		log.Fatalln("Failed to declare RabbitMQ queue:", err)
	}

	log.Println("Successfully connected to RabbitMQ")
	return conn, ch, q
}

// PublishJob sends a JSON payload to the queue
func PublishJob(ch *amqp.Channel, q amqp.Queue, body []byte) error {
	return ch.Publish(
		"",     // exchange
		q.Name, // routing key
		false,  // mandatory
		false,  // immediate
		amqp.Publishing{
			ContentType: "application/json",
			Body:        body,
		})
}