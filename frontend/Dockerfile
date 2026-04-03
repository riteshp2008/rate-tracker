# Frontend Dockerfile for NextJS
FROM node:18-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install --legacy-peer-deps

# Copy source code
COPY . .

# Expose port
EXPOSE 3000

# Start app in development mode (better for local development)
CMD ["npm", "run", "dev"]
