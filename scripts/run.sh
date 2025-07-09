#!/bin/bash
#SBATCH -A nvr_elm_llm                                                              #account
#SBATCH -p polar4,polar3,polar,grizzly                                         #partition
#SBATCH -t 04:00:00                                                                 #wall time limit, hr:min:sec
#SBATCH -N 1                                                                        #number of nodes
#SBATCH -J elm:mjv                                                       #job name
#SBATCH --array=0-302%303                                                          # 创建一个作业数组，包含从0到511的作业实例，每次最多并行运行40个实例
#SBATCH --gpus-per-node 1
#SBATCH --cpus-per-task 12
#SBATCH --mem-per-cpu 16G
#SBATCH -e /home/lezhao/lezhao/DOVER/output/slurm_log_dover/dev_error.log
#SBATCH -o /home/lezhao/lezhao/DOVER/output/slurm_log_dover/dev_out.log

job_shift=0
idx=$(($SLURM_ARRAY_TASK_ID + job_shift))
total=$(($SLURM_ARRAY_TASK_COUNT + job_shift))

export PATH="$HOME/miniforge3/envs/dover/bin:$PATH"

# data path
# DATA_PATH="data/InternData/debug_data_train/wan/"       # 69 zips
# DATA_PATH="data/InternData/debug_data_train/wan_slg/"   # 553 zips
# DATA_PATH="data/sora"        # 2651 zips
DATA_PATH="/home/lezhao/lezhao/sana-video/data/mjv" # 0 - 302 303 zips
# DATA_PATH="data/sora_new_0704" # 2651-3084 433 zips
# SAVE_DIR="output/sora"
# SAVE_DIR="output/sora_new_0704"
SAVE_DIR="output/mjv"
mkdir -p $SAVE_DIR

logdir=$SAVE_DIR/slurm_logs
mkdir -p $logdir

jname=$idx-of-$total

srun -e $logdir/error_$jname.log -o $logdir/slurm_$jname.log \
    bash -c "python run.py --job_id $idx --data_path $DATA_PATH --save_dir $SAVE_DIR"
