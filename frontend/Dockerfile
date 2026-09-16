# Cloud Run image for the React frontend: Vite build, served by nginx.
# Build context is ./frontend.
#
#   docker build --build-arg VITE_API_URL=https://... -t appt-frontend:local ./frontend
#
# NOTE: src/App.jsx is still the stock Vite starter page. This image builds and serves
# correctly, but what it serves is the scaffold, not a booking UI.

FROM node:22-alpine AS build

WORKDIR /app

# Vite inlines VITE_* at build time, so the backend URL is baked into the bundle here
# and cannot be changed by setting an env var on the running container.
ARG VITE_API_URL=/api
ENV VITE_API_URL=${VITE_API_URL}

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build


FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
