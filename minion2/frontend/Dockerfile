# Build stage
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .

# Set dynamic API URL for the build
ARG VITE_API_BASE=http://localhost:8001
ENV VITE_API_BASE=${VITE_API_BASE}

RUN npm run build

# Serve stage
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
