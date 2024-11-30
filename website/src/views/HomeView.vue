<template>
  <div id="app" class="container mt-5">
    <h1 class="text-center mb-4">YouClipAI</h1>
    
    <!-- Search Form -->
    <div class="form-group row">
      <div class="col-md-10">
        <input
          type="text"
          class="form-control"
          placeholder="Type your query (e.g., Austin Reaves workout clip)..."
          v-model="userQuery"
        />
      </div>
      <div class="col-md-2">
        <button
          class="btn btn-primary btn-block"
          @click="submitQuery"
          :disabled="loading"
        >
          <span v-if="loading" class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
          {{ loading ? " Searching..." : "Search" }}
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center mt-4">
      <div class="spinner-border text-primary" role="status">
        <span class="sr-only">Loading...</span>
      </div>
      <p class="mt-2">Processing your request...</p>
    </div>

    <!-- Progress Bar -->
    <div v-if="progress > 0 && progress < 100" class="mt-4">
      <div class="progress">
        <div
          class="progress-bar progress-bar-striped progress-bar-animated"
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
    <div v-if="transcriptions.length > 0" class="mt-4">
      <h3>Transcriptions:</h3>
      <ul class="list-group">
        <li v-for="(transcription, index) in transcriptions" :key="index" class="list-group-item">
          {{ transcription }}
        </li>
      </ul>
    </div>

    <!-- Search Results -->
    <div v-if="searchResults.length" class="mt-5">
      <h3>Search Results:</h3>
      <div v-for="(video, index) in searchResults" :key="index" class="card mb-3">
        <div class="card-body">
          <h5 class="card-title">{{ video.title }}</h5>
          <p class="card-text"><strong>Video ID:</strong> {{ video.video_id }}</p>
          <a
            :href="`https://www.youtube.com/watch?v=${video.video_id}`"
            class="btn btn-secondary"
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
      userQuery: "",
      progress: 0,
      loading: false,
      searchResults: [],
      transcriptions: [],
      apiBaseUrl: process.env.VUE_APP_API_BASE_URL || "http://127.0.0.1:5000",
    };
  },
  methods: {
    async submitQuery() {
      if (!this.userQuery.trim()) {
        alert("Please enter a query.");
        return;
      }
      this.loading = true;
      this.progress = 0;
      this.transcriptions = [];
      this.searchResults = [];

      try {
        // Send query to the backend
        const response = await axios.post(`${this.apiBaseUrl}/api/search`, {
          query: this.userQuery,
        });

        if (response.data.status === "success") {
          this.searchResults = response.data.videos || [];
          this.loading = false;
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
  },
};
</script>

<style scoped>
.container {
  max-width: 800px;
  margin: auto;
}

.spinner-border {
  width: 3rem;
  height: 3rem;
}

.card {
  border: 1px solid #ddd;
  border-radius: 8px;
}

.card-title {
  font-size: 1.25rem;
}

.btn-primary,
.btn-secondary {
  min-width: 100px;
}

.progress-bar {
  height: 25px;
}
</style>
