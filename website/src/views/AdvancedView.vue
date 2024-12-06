<template>
  <div id="app" class="container mt-5">
    <!-- Header -->
    <header class="text-center mb-4">
      <h1 class="display-4">YouClipAI - Advanced Search</h1>
      <p class="lead">Discover Clips That Match Your Query Instantly</p>
    </header>

    <!-- Query Input -->
    <section class="mt-5">
      <h3>Query:</h3>
      <textarea
        class="form-control form-control-lg mb-3"
        v-model="input_query"
        placeholder="Enter your query..."
        rows="3"
      ></textarea>
      <button class="btn btn-primary btn-block" @click="searchYoutube">
        <span v-if="loading" class="spinner-border spinner-border-sm"></span>
        {{ loading ? "Processing..." : "Fetch Video" }}
      </button>
    </section>

    <!-- Video List -->
    <section v-if="videos.length > 0" class="mt-5">
      <h3>Possible Matches:</h3>
      <ul class="list-group">
        <li
          v-for="(video, index) in videos"
          :key="video.id"
          class="list-group-item d-flex flex-column"
        >
          <div class="d-flex justify-content-between align-items-center">
            <span>{{ video.title }}</span>
            <div>
              <a
                :href="`https://www.youtube.com/watch?v=${video.id}`"
                class="btn btn-success btn-sm mr-2"
                target="_blank"
              >
                <i class="fas fa-play"></i>
              </a>

              <button
                class="btn btn-danger btn-sm ml-2"
                @click="deleteVideo(index)"
              >
                <i class="fas fa-trash"></i>
              </button>
            </div>
          </div>
          <!-- Progress -->
          <div v-if="video.progress > 0 && video.progress < 100" class="mt-3">
            <small>{{ video.currentStage }}</small>
            <div class="progress">
              <div
                class="progress-bar progress-bar-striped progress-bar-animated bg-info"
                :style="{ width: `${video.progress}%` }"
              ></div>
            </div>
          </div>
        </li>
      </ul>
      <button class="btn btn-secondary btn-block mt-3" @click="startAnalysis">
        Analyze
      </button>
    </section>

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
  </div>
</template>

<script>
import axios from "axios";

export default {
  data() {
    return {
      videos: [],
      current_video: null,
      videoClips: [],

      input_query:
        "I want to find the clip of Austin Reaves commenting about posting working out in gym during Laker's media day 2024.",
      loading: false,
      apiBaseUrl: process.env.VUE_APP_API_BASE_URL || "http://127.0.0.1:5000",
    };
  },
  methods: {
    deleteVideo(index) {
      this.videos.splice(index, 1);
    },

    async searchYoutube() {
      if (!this.input_query.trim()) {
        alert("Please enter a query.");
        return;
      }
      this.loading = true;
      this.videos = []; // Reset video list before starting a new search
      this.current_video = null;
      this.videoClips = [];

      try {
        const response = await axios.post(
          `${this.apiBaseUrl}/api/videos/advanced_search`,
          {
            query: this.input_query,
          }
        );

        if (response.data.status === "success") {
          // Ensure `this` context is preserved for `pollProgress`
          this.pollProgress(response.data.task_id);
        } else {
          alert("Error fetching videos.");
          this.loading = false;
        }
      } catch (error) {
        console.error("Error searching YouTube:", error);
        this.loading = false;
      }
    },

    async startAnalysis() {
      try {
        // Reset progress and stages for all videos
        for (const video of this.videos) {
          video.progress = 0;
          video.currentStage = "Starting";
        }
        this.videoClips = [];

        const response = await axios.post(
          `${this.apiBaseUrl}/api/videos/analyze`,
          {
            videos: this.videos,
            query: this.query,
          }
        );

        if (response.data.status === "success") {
          this.pollProgress(response.data.task_id);
        } else {
          alert("Error starting the analysis.");
        }
      } catch (error) {
        console.error("Error starting analysis:", error);
      }
    },

    pollProgress(taskId) {
      const interval = setInterval(async () => {
        try {
          const response = await axios.get(
            `${this.apiBaseUrl}/api/videos/progress/${taskId}`
          );
          const taskData = response.data;
          console.log("Task data:", taskData, this.videos);

          if (
            taskData.task_type === "advanced_search" &&
            taskData.status === "completed"
          ) {
            this.query = taskData.data.query;
            this.videos = taskData.data.videos;
            clearInterval(interval);
            this.loading = false;
            console.log("Videos:", this.videos);
          } else if (taskData.task_type === "analyze") {
            // Update video progress reactively
            if (taskData.current_video !== null) {
              this.videos[taskData.current_video].progress = taskData.progress;
              this.videos[taskData.current_video].currentStage =
                taskData.subtask_type;
              for (
                let videoIndex = 0;
                videoIndex < this.videos.length;
                videoIndex++
              ) {
                if (videoIndex !== taskData.current_video) {
                  this.videos[videoIndex].progress = 0;
                }
              }
            }

            if (
              taskData.status === "completed" ||
              taskData.status === "error"
            ) {
              clearInterval(interval);
              this.videoClips = taskData.data || [];
              console.log("Video clips:", this.videoClips);
            }
          }
        } catch (error) {
          console.error("Error polling progress:", error);
          clearInterval(interval);
        }
      }, 1000);
    },

    formatTime(seconds) {
      const minutes = Math.floor(seconds / 60);
      const remainingSeconds = Math.floor(seconds % 60);
      return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}`;
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

h5 {
  margin-bottom: 0;
}
/* Ensure the buttons stay aligned to the right */
.list-group-item {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  margin-bottom: 10px;
}

.video-title {
  flex-grow: 1;
  margin-right: 20px; /* Add spacing between title and buttons */
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.button-group {
  display: flex;
  gap: 10px; /* Add spacing between buttons */
}
</style>
