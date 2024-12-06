<template>
  <div id="app" class="container mt-5">
    <!-- Header Section -->
    <header class="text-center mb-4">
      <h1 class="display-4">YouClipAI - Quick Start</h1>
      <p class="lead">
        Easily Analyze and Extract Clips from Any YouTube Video URL
      </p>
    </header>

    <!-- Search Form -->
    <section class="mb-4">
      <div class="form-group row align-items-center">
        <div class="col-md-9">
          <input
            type="text"
            class="form-control form-control-lg"
            placeholder="Enter YouTube URL"
            v-model="youtubeURL"
            aria-label="YouTube URL"
          />
        </div>
        <div class="col-md-3">
          <button
            class="btn btn-primary btn-lg btn-block"
            @click="submitQuery"
            :disabled="loading"
            aria-label="Fetch Video Button"
          >
            <span
              v-if="loading"
              class="spinner-border spinner-border-sm"
            ></span>
            {{ loading ? "Processing..." : "Fetch Video" }}
          </button>
        </div>
      </div>
    </section>

    <!-- Video Information Section -->
    <section v-if="video" class="mt-5 text-center">
      <div class="card">
        <div class="card-body">
          <h3 class="card-title mb-3">{{ video.title }}</h3>
          <iframe
            :src="videoEmbedUrl"
            width="100%"
            height="315"
            frameborder="0"
            allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowfullscreen
          ></iframe>
          <button
            class="btn btn-secondary mt-3"
            @click="startAnalysis"
            :disabled="loading"
            aria-label="Analyze Video Button"
          >
            Analyze Video
          </button>
        </div>
      </div>
    </section>

    <!-- Query Input Section -->
    <section v-if="analyzeMetadata" class="mt-5">
      <h3>Query the Video:</h3>
      <textarea
        class="form-control form-control-lg mb-3"
        placeholder="Enter your query here"
        rows="3"
        v-model="query"
        aria-label="Query Input"
      ></textarea>
      <button
        class="btn btn-primary btn-block"
        @click="searchContent"
        :disabled="loading"
        aria-label="Search Query Button"
      >
        Search
      </button>
    </section>

    <!-- Video Clips Section -->
    <section v-if="videoClips.length > 0" class="mt-5">
      <h3>Extracted Clips:</h3>
      <div v-for="(clip, index) in videoClips" :key="index" class="mb-4">
        <h5>
          Clip {{ index + 1 }}: {{ formatTime(clip.start_time) }} -
          {{ formatTime(clip.end_time) }}
        </h5>
        <video
          width="100%"
          height="315"
          controls
          :src="clip.video_clip_path"
          aria-label="Video Clip Player"
        >
          Your browser does not support the video tag.
        </video>
      </div>
    </section>

    <!-- Progress Bar -->
    <div v-if="progress > 0 && progress < 100" class="mt-4">
      <div class="progress" style="height: 30px">
        <div
          class="progress-bar progress-bar-striped progress-bar-animated bg-info"
          role="progressbar"
          :style="{ width: `${progress}%` }"
          aria-valuenow="progress"
          aria-valuemin="0"
          aria-valuemax="100"
        >
          {{ progress }}%
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
      youtubeURL:
        "https://www.youtube.com/watch?v=cNXxqE7hs9U&ab_channel=TheSportingTribune",
      query:
        "I want to find the clip of Austin Reaves commenting about posting working out in gym during Laker's media day 2024.",
      progress: 0,
      loading: false,
      video: null,
      videoClips: [],
      analyzeMetadata: null,
      apiBaseUrl: process.env.VUE_APP_API_BASE_URL || "http://127.0.0.1:5000",
    };
  },
  computed: {
    videoEmbedUrl() {
      if (this.video && this.video.url) {
        // Extract the video ID from the URL and create the embed link
        const videoId = this.video.url.match(/v=([a-zA-Z0-9_-]{11})/);
        if (videoId && videoId[1]) {
          return `https://www.youtube.com/embed/${videoId[1]}`;
        }
      }
      return "";
    },
  },
  methods: {
    async submitQuery() {
      if (!this.youtubeURL.trim()) {
        alert("Please enter a YouTube URL.");
        return;
      }
      this.loading = true;
      this.resetData();

      try {
        const response = await axios.post(
          `${this.apiBaseUrl}/api/videos/fetch`,
          {
            youtubeURL: this.youtubeURL,
          }
        );

        if (response.data.status === "success") {
          this.pollProgress(response.data.task_id);
        } else {
          this.handleError("Error starting the process.");
        }
      } catch (error) {
        this.handleError("Failed to send query.");
      }
    },

    async pollProgress(taskId) {
      const interval = setInterval(async () => {
        try {
          const response = await axios.get(
            `${this.apiBaseUrl}/api/videos/progress/${taskId}`
          );

          if (response.data.status === "error") {
            clearInterval(interval);
            this.handleError("Error during processing.");
            return;
          }

          console.log(response.data);

          this.progress = response.data.progress;
          if (response.data.task_type === "fetch_video") {
            this.video = response.data.data || {};
          } else if (response.data.task_type === "analyze_asr") {
            this.analyzeMetadata = response.data.data || null;
          } else if (response.data.task_type === "search_content") {
            this.videoClips = response.data.data || [];
          }

          if (this.progress >= 100) {
            clearInterval(interval);
            this.loading = false;
          }
        } catch (error) {
          clearInterval(interval);
          this.handleError("Error polling progress.");
        }
      }, 1000);
    },

    async startAnalysis() {
      try {
        this.analyzeMetadata = null;
        const response = await axios.post(
          `${this.apiBaseUrl}/api/videos/analyze_asr`,
          {
            video: this.video,
          }
        );

        if (response.data.status === "success") {
          this.pollProgress(response.data.task_id);
        } else {
          this.handleError("Error starting the analysis.");
        }
      } catch (error) {
        this.handleError("Failed to start analysis.");
      }
    },

    async searchContent() {
      if (!this.query.trim()) {
        alert("Please enter a query.");
        return;
      }

      try {
        const response = await axios.post(
          `${this.apiBaseUrl}/api/videos/search_content`,
          {
            query: this.query,
            metadata: this.analyzeMetadata,
          }
        );

        if (response.data.status === "success") {
          this.pollProgress(response.data.task_id);
        } else {
          this.handleError("Error searching content.");
        }
      } catch (error) {
        this.handleError("Failed to search content.");
      }
    },

    formatTime(seconds) {
      const minutes = Math.floor(seconds / 60);
      const remainingSeconds = Math.floor(seconds % 60);
      return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}`;
    },

    resetData() {
      this.progress = 0;
      this.video = null;
      this.analyzeMetadata = null;
      this.videoClips = [];
    },

    handleError(message) {
      this.loading = false;
      alert(message);
    },
  },
};
</script>

<style scoped>
.container {
  max-width: 1000px;
  margin: auto;
  padding: 20px;
}

header {
  background-color: #f8f9fa;
  padding: 20px;
  border-radius: 10px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.card {
  border: 1px solid #ddd;
  border-radius: 8px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.card-title {
  font-size: 1.5rem;
}

textarea {
  resize: none;
}

.progress-bar {
  height: 30px;
  line-height: 30px;
  text-align: center;
  font-weight: bold;
  color: #fff;
}
</style>
