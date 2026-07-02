# Instructions go here 

# Use Node version 22 as the base image
FROM node:22    

# Set the working directory in the container
WORKDIR /app

# Copy package.json and package-lock.json to the working directory
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application code to the working directory
COPY . .

# Set the environment variable for production
ENV PORT=9000

# Expose the port so our computer can access the application
EXPOSE 9000

# Start the application
CMD ["npm", "start"]    