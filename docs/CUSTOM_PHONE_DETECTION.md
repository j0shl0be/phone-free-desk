# Using Custom Phone Detection Models

The system uses a **hybrid detection approach**:
- **YOLOv8** for phone detection (COCO "cell phone" class, ID 67)
- **MediaPipe Hands** for detecting when your hand reaches for the phone
- **MediaPipe Face** for targeting the spray

However, **COCO's phone detection is not ideal for phones lying flat on desks** - it was trained mostly on phones held up prominently in selfies.

If you're having trouble detecting your phone (but hand/face detection works fine), you have several options:

## Option 1: Adjust Confidence Threshold (Easiest)

Edit `config/settings.yaml`:

```yaml
vision:
  phone_confidence: 0.2  # Lower = more sensitive (try 0.2, 0.15, or even 0.1)
  person_confidence: 0.5
  debug: true  # Enable to see what YOLO detects
```

Run test to see what's being detected:

```bash
python3 scripts/test_detection.py
```

With `debug: true`, you'll see console output showing all detections and their confidence scores.

## Option 2: Use a Roboflow Phone Detection Model (Recommended)

Roboflow has pre-trained YOLOv8 models specifically for phone detection:

### Available Models:

1. **[Phone Detection by YOLOv8 Projects](https://universe.roboflow.com/yolov8-projects-0cryt/phone-detection-nss2y)**
   - 114 training images
   - Specifically trained for phones in various orientations

2. **[Cellphone-Yolov8-Training by Hope](https://universe.roboflow.com/hope-qiflt/cellphone-yolov8-training)**
   - 294 training images
   - Good for cellphone detection in natural scenes

3. **[Mobile phone detection](https://universe.roboflow.com/realtime-mobile-phone-usage-detection-in-everyday-scenarios-using-yolo/mobile-phone-detection-mtsje-xhoma/dataset/1)**
   - 1,674 training images
   - "Real-time Mobile Phone Usage Detection in Everyday Scenarios"
   - **Best option for phones on desks**

### How to Use a Roboflow Model:

#### Step 1: Install Roboflow

```bash
pip install roboflow
```

#### Step 2: Download the Model

```python
from roboflow import Roboflow

# Initialize with your API key (get free key from roboflow.com)
rf = Roboflow(api_key="YOUR_API_KEY")

# Download the model
project = rf.workspace("realtime-mobile-phone-usage-detection-in-everyday-scenarios-using-yolo").project("mobile-phone-detection-mtsje-xhoma")
dataset = project.version(1).download("yolov8")
```

This downloads the model to your local machine.

#### Step 3: Train or Use Pre-trained Weights

```bash
# Option A: Use their pre-trained model (if available)
# Download the .pt weights file from the Roboflow project

# Option B: Train on your own setup (recommended for best results)
cd mobile-phone-detection-1
yolo task=detect mode=train model=yolov8n.pt data=data.yaml epochs=50 imgsz=640
```

Training takes 10-30 minutes on a decent GPU, or you can use Roboflow's cloud training.

#### Step 4: Configure phone-free-desk to Use Custom Model

Edit `config/settings.yaml`:

```yaml
vision:
  model: 'path/to/your/custom_model.pt'  # Path to Roboflow model weights
  phone_confidence: 0.5  # Can be higher with specialized model
  person_confidence: 0.5
```

#### Step 5: Update Class ID

Edit `src/vision/detector.py` if the custom model uses different class IDs:

```python
# Find this line:
self.CLASS_PHONE = 67  # cell phone in COCO

# Change to:
self.CLASS_PHONE = 0  # or whatever class ID your model uses (check data.yaml)
```

## Option 3: Train Your Own Model (Best Results)

For the absolute best results, train a model on **your specific phone and desk setup**:

### Step 1: Collect Training Data

1. Take 50-100 photos of your phone on your desk from the camera angle
2. Include different positions, orientations, lighting conditions
3. Include photos with and without your hand near the phone

### Step 2: Annotate Images

Use [Roboflow](https://roboflow.com) to label your phone in each image:

1. Upload images to Roboflow
2. Draw bounding boxes around the phone
3. Label as "phone"
4. Export as "YOLOv8" format

### Step 3: Train Model

```bash
# Roboflow generates a data.yaml file
yolo task=detect mode=train model=yolov8n.pt data=data.yaml epochs=100 imgsz=640
```

On Raspberry Pi, this could take hours. Consider using:
- Google Colab (free GPU)
- Roboflow's cloud training
- Your desktop/laptop with GPU

### Step 4: Deploy Model

Copy the trained `best.pt` weights to your Pi and update config:

```yaml
vision:
  model: '/path/to/best.pt'
  phone_confidence: 0.6  # Custom models are more confident
```

## Comparing Options

| Option | Effort | Accuracy | Speed | Best For |
|--------|--------|----------|-------|----------|
| Lower threshold | 1 min | Medium | Fast | Quick fix |
| Roboflow pre-trained | 30 min | Good | Fast | Most users |
| Train custom model | 2-3 hours | Excellent | Fast | Best results |

## Troubleshooting

### Phone still not detected?

1. **Enable debug mode** to see what YOLO finds:
   ```yaml
   vision:
     debug: true
   ```

2. **Check what classes are being detected**:
   ```bash
   python3 scripts/test_detection.py
   ```

   Look at console output to see if YOLO detects anything at all

3. **Try detecting with 0 confidence** to see everything:
   ```yaml
   vision:
     phone_confidence: 0.01  # Detect everything
   ```

4. **Verify camera works**:
   ```bash
   python3 -c "import cv2; cap = cv2.VideoCapture(0); print(cap.read())"
   ```

### Performance issues?

- Increase `frame_skip` to process fewer frames:
  ```yaml
  vision:
    frame_skip: 3  # Process every 3rd frame
  ```

- Use a lighter model (but less accurate):
  ```yaml
  vision:
    model: 'yolov8n.pt'  # n = nano (fastest, least accurate)
                          # s = small
                          # m = medium
                          # l = large
                          # x = extra large
  ```

## Resources

- [Ultralytics YOLOv8 Docs](https://docs.ultralytics.com)
- [COCO Dataset Classes](https://docs.ultralytics.com/datasets/detect/coco/)
- [Roboflow Universe](https://universe.roboflow.com)
- [How to Train YOLOv8](https://blog.roboflow.com/how-to-train-yolov8-on-a-custom-dataset/)
