import json
import os
import subprocess
import tempfile
import zipfile
from glob import glob

from tqdm import tqdm
import yaml

from evaluate_sample import calculate_dover_score, build_model

def load_existing_results(output_json):
    """加载已存在的结果文件"""
    if os.path.exists(output_json):
        try:
            with open(output_json, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"warning: cannot load results file {output_json}: {e}")
    return {}


def save_results(output_json, scores):
    """保存结果到JSON文件"""
    try:
        with open(output_json, 'w') as f:
            json.dump(scores, f, indent=2)
        print(f"saved {len(scores)} results to {output_json}")
    except Exception as e:
        print(f"error saving results file {output_json}: {e}")


def process_zip(zip_path, output_json, save_interval=5000):
    """
    处理zip文件，基于已存在的JSON文件判断进度
    save_interval: 每处理多少个文件保存一次结果
    """
    # 加载现有结果
    scores = load_existing_results(output_json)
    
    with zipfile.ZipFile(zip_path, "r") as zf:
        # 获取所有mp4文件列表
        mp4_files = [name for name in zf.namelist() if name.endswith(".mp4")]
        total_files = len(mp4_files)
        
        print(f"found {total_files} video files")
        
        # 检查是否已完全处理完成
        if len(scores) >= total_files:
            print(f"all {total_files} files already processed, skipping")
            return scores
        
        print(f"resuming from {len(scores)} processed files")
        
        # 创建进度条
        pbar = tqdm(total=total_files, initial=len(scores))
        pbar.set_description("processing video files")
        
        files_processed_since_save = 0
        
        try:
            for name in mp4_files:
                if "mjv" in zip_path:
                    key = os.path.splitext(name)[0]
                else:
                    key = os.path.splitext(os.path.basename(name))[0]
                # 跳过已处理的文件
                if key in scores:
                    continue
                
                # 提取mp4到临时文件并计算分数
                try:
                    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=True) as tmp:
                        tmp.write(zf.read(name))
                        tmp.flush()
                        score, technical, aesthetic = calculate_dover_score(opt, evaluator, tmp.name)
                        scores[key] = {"dover_score": score, "technical_score": technical, "aesthetic_score": aesthetic}
                        files_processed_since_save += 1
                        
                        pbar.set_postfix({"current": key[:20] + "..." if len(key) > 20 else key})
                        pbar.update(1)
                        
                except Exception as e:
                    print(f"error processing file {name}: {e}")
                    continue
                
                # 定期保存结果
                if files_processed_since_save >= save_interval:
                    save_results(output_json, scores)
                    files_processed_since_save = 0
                    print(f"{len(scores)}/{total_files} files processed, progress saved")
        
        except KeyboardInterrupt:
            print("\ndetected interrupt signal, saving progress...")
        except Exception as e:
            print(f"\nerror during processing: {e}")
        finally:
            # 最终保存
            save_results(output_json, scores)
            pbar.close()
            print(f"finished processing {len(scores)}/{total_files} files")
    
    return scores


def main(zip_path_or_dir, save_dir=None, save_interval=5000):
    # 判断输入路径是单个zip文件还是目录
    if zip_path_or_dir.endswith(".zip") and os.path.isfile(zip_path_or_dir):
        # 处理单个zip文件
        zip_files = [zip_path_or_dir]
    else:
        # 处理目录中的所有zip文件
        zip_files = glob(os.path.join(zip_path_or_dir, "*.zip"))

    for zip_path in zip_files:
        base = os.path.splitext(os.path.basename(zip_path))[0]
        if save_dir is not None:
            # 如果指定了save_dir，使用指定的目录
            os.makedirs(save_dir, exist_ok=True)
            output_json = os.path.join(save_dir, f"{base}_dover.json")
        else:
            # 否则使用zip文件所在的目录
            output_json = os.path.join(os.path.dirname(zip_path), f"{base}_dover.json")
        print(f"processing {zip_path}")
        print(f"result file: {output_json}")
        
        scores = process_zip(zip_path, output_json, save_interval)
        print(f"finished processing {zip_path}, {len(scores)} results")


def zip_dir(source_dir, zip_path):
    with zipfile.ZipFile(zip_path, "w") as zf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, source_dir)
                zf.write(abs_path, rel_path)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--zip_path", type=str, help="zip文件路径或包含zip文件的目录")
    parser.add_argument("--job_id", type=int, help="slurm job id，会自动生成对应的zip文件名")
    parser.add_argument("--data_path", type=str, help="数据根目录，配合job_id使用")
    parser.add_argument("--save_dir", type=str, help="指定JSON结果文件的保存目录，如果不指定则保存在zip文件所在目录")
    parser.add_argument("-si", "--save_interval", type=int, default=2000, help="每处理多少个文件保存一次结果，默认2000")
    args = parser.parse_args()

    # zip a dir
    # zip_dir('data/InternData/debug_data_train/video_for_vmaf_motion_score_test', 'data/InternData/debug_data_train/video_for_vmaf_motion_score_test.zip')

    # build model all together
    with open("./dover.yml", "r") as f:
        opt = yaml.safe_load(f)
    evaluator = build_model(opt)

    if args.job_id is not None:
        # 使用job_id生成zip文件路径
        if args.data_path is None:
            raise ValueError("must specify data_path when job_id is provided")
        zip_filename = f"{args.job_id:08d}.zip"
        zip_path = os.path.join(args.data_path, zip_filename)
        main(zip_path, args.save_dir, args.save_interval)
    else:
        # 使用原来的zip_path参数
        if args.zip_path is None:
            raise ValueError("must specify zip_path or job_id")
        main(args.zip_path, args.save_dir, args.save_interval)
