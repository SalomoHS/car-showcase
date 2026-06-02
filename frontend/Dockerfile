# Stage 1: Build the React application
FROM node:20-alpine AS build

WORKDIR /app

# Copy package.json and package-lock.json
COPY package*.json ./

# Install dependencies
RUN npm ci --legacy-peer-deps || npm install --legacy-peer-deps

# Copy the rest of the application code
COPY . .

# Build the app
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/build /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]