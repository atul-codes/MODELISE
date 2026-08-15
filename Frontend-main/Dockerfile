# ---------- BUILD STAGE ----------
FROM node:22-alpine AS build

# Set working dir to app root
WORKDIR /app

# Copy package files first (cache optimization)
COPY package*.json ./

RUN npm install

# Copy entire project
COPY . .

# Build React app
RUN npm run build


# ---------- RUNTIME STAGE ----------
FROM node:22-alpine

WORKDIR /app

# For serving the static build
RUN npm install -g serve

# Copy the build output from previous stage
COPY --from=build /app/dist ./dist

EXPOSE 3000

CMD ["serve", "-s", "dist", "-l", "3000"]