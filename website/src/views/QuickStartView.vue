<template>
  <div id="app" class="container mt-5">
    <div class="text-center mb-4">
      <h1 class="display-4">YouClipAI - Quick Start</h1>
      <p class="lead">Analyze and extract information from YouTube videos easily.</p>
    </div>

    <!-- Search Form -->
    <div class="form-group row align-items-center mb-4">
      <div class="col-md-9">
        <input
          type="text"
          class="form-control form-control-lg"
          placeholder="Enter YouTube URL (e.g., https://www.youtube.com/watch?v=...)"
          v-model="youtubeURL"
        />
      </div>
      <div class="col-md-3">
        <button
          class="btn btn-primary btn-lg btn-block"
          @click="submitQuery"
          :disabled="loading"
        >
          <span v-if="loading" class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
          {{ loading ? " Processing..." : "Analyze Video" }}
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center mt-4">
      <div class="spinner-border text-primary" role="status">
        <span class="sr-only">Loading...</span>
      </div>
      <p class="mt-2">Processing your request, please wait...</p>
    </div>

    <!-- Progress Bar -->
    <div v-if="progress > 0 && progress < 100" class="mt-4">
      <div class="progress" style="height: 30px;">
        <div
          class="progress-bar progress-bar-striped progress-bar-animated bg-success"
          role="progressbar"
          :style="{ width: `${progress}%` }"
          :aria-valuenow="progress"
          aria-valuemin="0"
          aria-valuemax="100"
        >
          {{ progress }}%
        </div>
      </div>
    </div>

    <!-- Transcriptions -->
    <div v-if="transcriptions.length > 0" class="mt-5">
      <h3>Transcriptions:</h3>
      <div class="card mt-3">
        <div class="card-body">
          <ul class="list-group list-group-flush">
            <li v-for="(transcription, index) in transcriptions" :key="index" class="list-group-item">
              <p class="mb-1"><strong>Part {{ index + 1 }}:</strong></p>
              <p class="mb-0">{{ transcription }}</p>
            </li>
          </ul>
        </div>
      </div>
    </div>

    <!-- Search Result -->
    <div v-if="video" class="mt-5">
      <h3>Video Search Result:</h3>
      <div class="card mt-3">
        <div class="card-body">
          <h5 class="card-title">{{ video.title }}</h5>
          <a
            :href="`${video.url}`"
            class="btn btn-secondary mt-3"
            target="_blank"
            rel="noopener noreferrer"
          >
            Watch on YouTube
          </a>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";

export default {
  data() {
    return {
      youtubeURL: "",
      progress: 0,
      loading: false,
      video: null,
      transcriptions: [],
      apiBaseUrl: process.env.VUE_APP_API_BASE_URL || "http://127.0.0.1:5000",
    };
  },
  methods: {
    async submitQuery() {
      if (!this.youtubeURL.trim()) {
        alert("Please enter a YouTube URL.");
        return;
      }
      this.loading = true;
      this.progress = 0;
      this.transcriptions = [];
      this.video = null;

      try {
        // Send query to the backend
        const response = await axios.post(`${this.apiBaseUrl}/api/videos/analyze`, {
          youtubeURL: this.youtubeURL,
        });

        if (response.data.status === "success") {
          const taskId = response.data.task_id;
          this.pollProgress(taskId);
        } else {
          alert("Error starting the process.");
          this.loading = false;
        }
      } catch (error) {
        console.error("Error:", error);
        alert("Failed to send query.");
        this.loading = false;
      }
    },

    async pollProgress(taskId) {
      const interval = setInterval(async () => {
        try {
          const progressResponse = await axios.get(`${this.apiBaseUrl}/api/videos/progress/${taskId}`);
          this.progress = progressResponse.data.progress;
          this.video = progressResponse.data.video || {};

          // Show progress only when greater than 0
          if (this.progress > 0) {
            this.loading = false;
          }

          if (this.progress >= 100) {
            clearInterval(interval);
            this.loading = false;
            this.transcriptions = progressResponse.data.transcriptions || [];
          }
        } catch (error) {
          console.error("Error polling progress:", error);
          clearInterval(interval);
          this.loading = false;
          alert("Error polling progress.");
        }
      }, 1000); // Poll every second
    },
  },
};
</script>

<style scoped>
.container {
  max-width: 800px;
  margin: auto;
  padding: 20px;
}

.spinner-border {
  width: 2.5rem;
  height: 2.5rem;
}

.card {
  border: 1px solid #ddd;
  border-radius: 8px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.card-title {
  font-size: 1.5rem;
}

.btn-primary,
.btn-secondary {
  min-width: 150px;
}

.progress-bar {
  height: 30px;
  line-height: 30px;
  text-align: center;
  font-weight: bold;
  color: #fff;
}
</style>
