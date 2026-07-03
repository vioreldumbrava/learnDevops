package main

import (
	"fmt"
	"sync"
	"time"
)

// 1. A goroutine is just a function launched with the `go` keyword.
// It runs concurrently with the caller.
func sayHello(name string, done chan<- string) {
	time.Sleep(100 * time.Millisecond) // pretend to do work
	done <- "hello from " + name       // send the result over the channel
}

// 2. A worker in a worker pool: receives jobs from one channel,
// sends results to another. `<-chan` = receive-only, `chan<-` = send-only.
func worker(id int, jobs <-chan int, results chan<- string) {
	for job := range jobs { // loop until the jobs channel is closed
		time.Sleep(50 * time.Millisecond) // simulate work
		results <- fmt.Sprintf("worker %d processed job %d", id, job)
	}
}

func main() {
	// --- Part 1: launching a goroutine and getting a value back ---
	fmt.Println("=== 1. goroutine + channel ===")

	done := make(chan string) // unbuffered channel of strings
	go sayHello("goroutine-1", done)

	// main would exit before the goroutine runs if we didn't wait.
	// Receiving from the channel BLOCKS until a value is sent —
	// this is both the communication AND the synchronization.
	msg := <-done
	fmt.Println(msg)

	// --- Part 2: unbuffered vs buffered channels ---
	fmt.Println("\n=== 2. buffered channel ===")

	// Unbuffered: send blocks until someone receives (a handoff).
	// Buffered: send only blocks when the buffer is full.
	buffered := make(chan int, 3)
	buffered <- 1 // these don't block: buffer has room
	buffered <- 2
	buffered <- 3
	fmt.Println("received:", <-buffered, <-buffered, <-buffered)

	// --- Part 3: WaitGroup — waiting for N goroutines to finish ---
	fmt.Println("\n=== 3. sync.WaitGroup ===")

	var wg sync.WaitGroup
	for i := 1; i <= 3; i++ {
		wg.Add(1) // register one more goroutine to wait for
		go func(n int) {
			defer wg.Done() // signal completion when this function returns
			fmt.Printf("goroutine %d finished\n", n)
		}(i)
	}
	wg.Wait() // block until every Done() has been called

	// --- Part 4: worker pool — fan-out work, fan-in results ---
	fmt.Println("\n=== 4. worker pool ===")

	jobs := make(chan int, 5)
	results := make(chan string, 5)

	for w := 1; w <= 3; w++ { // 3 workers share the same jobs channel
		go worker(w, jobs, results)
	}

	for j := 1; j <= 5; j++ {
		jobs <- j
	}
	close(jobs) // tells workers' `range jobs` loops to stop

	for r := 1; r <= 5; r++ { // collect exactly as many results as jobs sent
		fmt.Println(<-results)
	}

	// --- Part 5: select — waiting on multiple channels at once ---
	fmt.Println("\n=== 5. select ===")

	fast := make(chan string)
	slow := make(chan string)
	go func() { time.Sleep(30 * time.Millisecond); fast <- "fast result" }()
	go func() { time.Sleep(300 * time.Millisecond); slow <- "slow result" }()

	// select blocks until ONE of its cases is ready.
	select {
	case msg := <-fast:
		fmt.Println("got:", msg)
	case msg := <-slow:
		fmt.Println("got:", msg)
	case <-time.After(1 * time.Second): // common timeout pattern
		fmt.Println("timed out")
	}

	// --- Part 6: range over a closed channel (producer/consumer) ---
	fmt.Println("\n=== 6. close + range ===")

	numbers := make(chan int)
	go func() {
		for i := 1; i <= 4; i++ {
			numbers <- i * i
		}
		close(numbers) // the producer closes; receivers must never close
	}()

	for n := range numbers { // exits automatically when channel is closed
		fmt.Println("square:", n)
	}
}
