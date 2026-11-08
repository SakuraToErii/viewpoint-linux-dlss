#pragma once
#include <pthread.h>
#include <mutex>
#include <condition_variable>
#include <functional>
#include <exception>
#include <stdexcept>
namespace {
class NgxWorker {
    std::mutex serial, mutex;
    std::condition_variable cv;
    std::function<void()> task;
    bool ready=false, done=false, stop=false;
    pthread_t thread{};
    static void* entry(void* p){static_cast<NgxWorker*>(p)->loop();return nullptr;}
    void loop(){
        std::unique_lock<std::mutex> lock(mutex);
        while(true){cv.wait(lock,[&]{return ready||stop;});if(stop)return;
            auto fn=std::move(task);ready=false;lock.unlock();fn();lock.lock();done=true;cv.notify_all();}
    }
public:
    NgxWorker(){pthread_attr_t attr;pthread_attr_init(&attr);pthread_attr_setstacksize(&attr,64u<<20);
        int result=pthread_create(&thread,&attr,entry,this);pthread_attr_destroy(&attr);
        if(result)throw std::runtime_error("cannot start DLSSG SDK worker");}
    ~NgxWorker(){{std::lock_guard<std::mutex> lock(mutex);stop=true;cv.notify_all();}pthread_join(thread,nullptr);}
    void run(std::function<void()> fn){std::lock_guard<std::mutex> single(serial);std::unique_lock<std::mutex> lock(mutex);
        std::exception_ptr error;task=[&]{try{fn();}catch(...){error=std::current_exception();}};
        ready=true;done=false;cv.notify_all();cv.wait(lock,[&]{return done;});if(error)std::rethrow_exception(error);}
};
NgxWorker& worker(){static NgxWorker instance;return instance;}
}
